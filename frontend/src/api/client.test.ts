import { describe, expect, it, vi } from 'vitest'
import { ApiClient, ApiError, readCsrfCookie } from './client'

const json = (status: number, body: unknown = {}) =>
  new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('cookie API client', () => {
  it('includes credentials and CSRF on mutations, handles an empty 204', async () => {
    const transport = vi.fn<typeof fetch>().mockResolvedValue(json(204))
    const client = new ApiClient('https://unit.invalid', transport, () => 'signed-csrf')
    await expect(client.request('/resource', { method: 'DELETE' })).resolves.toBeUndefined()
    const options = transport.mock.calls[0]?.[1]
    expect(options?.credentials).toBe('include')
    expect(new Headers(options?.headers).get('X-CSRF-Token')).toBe('signed-csrf')
    expect(new Headers(options?.headers).has('Authorization')).toBe(false)
  })

  it('only reads the named CSRF cookie and safely decodes it', () => {
    document.cookie = 'other_token=not-csrf; Path=/'
    expect(readCsrfCookie()).toBeUndefined()
    document.cookie = 'csrf_token=nonce%2Esignature; Path=/'
    expect(readCsrfCookie()).toBe('nonce.signature')
  })

  it('coalesces concurrent 401s into one refresh and retries each request once', async () => {
    let fresh = false
    let refreshCount = 0
    const transport = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith('/auth/refresh')) {
        refreshCount++
        fresh = true
        return json(204)
      }
      if (String(url).endsWith('/users/me')) return json(fresh ? 200 : 401)
      return json(fresh ? 200 : 401, fresh ? { ok: true } : { detail: 'Not authenticated' })
    })
    const client = new ApiClient('https://unit.invalid', transport, () => 'signed-csrf')
    const results = await Promise.all([
      client.request('/a'),
      client.request('/b'),
      client.request('/c'),
    ])
    expect(results).toEqual([{ ok: true }, { ok: true }, { ok: true }])
    expect(refreshCount).toBe(1)
    expect(transport.mock.calls.filter(([url]) => String(url).endsWith('/a'))).toHaveLength(2)
  })

  it('probes shared cookies inside the cross-tab lock before rotating again', async () => {
    let tail: Promise<unknown> = Promise.resolve()
    const lock = <T>(task: () => Promise<T>): Promise<T> => {
      const result = tail.then(task)
      tail = result.catch(() => undefined)
      return result
    }
    let fresh = false
    let refreshCount = 0
    const transport = vi.fn<typeof fetch>(async (url) => {
      if (String(url).endsWith('/auth/refresh')) {
        refreshCount++
        fresh = true
        return json(204)
      }
      return json(fresh ? 200 : 401, {})
    })
    const firstTab = new ApiClient('https://unit.invalid', transport, () => 'csrf', lock)
    const secondTab = new ApiClient('https://unit.invalid', transport, () => 'csrf', lock)
    await Promise.all([firstTab.request('/a'), secondTab.request('/b')])
    expect(refreshCount).toBe(1)
  })

  it('does not refresh when another tab already renewed the access cookie', async () => {
    const transport = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json(401))
      .mockResolvedValueOnce(json(200))
      .mockResolvedValueOnce(json(200, { ok: true }))
    const client = new ApiClient('https://unit.invalid', transport, () => 'csrf')
    await expect(client.request('/resource')).resolves.toEqual({ ok: true })
    expect(transport.mock.calls.some(([url]) => String(url).endsWith('/auth/refresh'))).toBe(false)
  })

  it.each([401, 403])(
    'expires UI session when refresh returns %i, without looping',
    async (status) => {
      const transport = vi.fn<typeof fetch>(async (url) =>
        json(String(url).endsWith('/auth/refresh') ? status : 401),
      )
      const client = new ApiClient('https://unit.invalid', transport, () => 'csrf')
      const listener = vi.fn()
      client.subscribe(listener)
      await expect(client.request('/resource')).rejects.toMatchObject({ status: 401 })
      expect(listener).toHaveBeenCalledWith('expired')
      expect(transport).toHaveBeenCalledTimes(3)
    },
  )

  it('rejects a second 401 after successful refresh instead of retrying again', async () => {
    const transport = vi.fn<typeof fetch>(async (url) =>
      json(String(url).endsWith('/auth/refresh') ? 204 : 401),
    )
    const client = new ApiClient('https://unit.invalid', transport, () => 'csrf')
    await expect(client.request('/resource')).rejects.toMatchObject({ status: 401 })
    expect(
      transport.mock.calls.filter(([url]) => String(url).endsWith('/auth/refresh')),
    ).toHaveLength(1)
    expect(transport.mock.calls.filter(([url]) => String(url).endsWith('/resource'))).toHaveLength(
      2,
    )
  })

  it('never retries a forbidden mutation or public auth error', async () => {
    const transport = vi
      .fn<typeof fetch>()
      .mockResolvedValue(json(403, { detail: 'Invalid CSRF token' }))
    const client = new ApiClient('https://unit.invalid', transport, () => 'csrf')
    await expect(
      client.request('/resource', { method: 'PATCH', body: { quantity: 5 } }),
    ).rejects.toMatchObject({ status: 403 })
    expect(transport).toHaveBeenCalledTimes(1)
    transport.mockResolvedValue(json(401))
    await expect(
      client.authAction('/auth/login', { email: 'unit@example.com', password: 'synthetic' }),
    ).rejects.toMatchObject({ status: 401 })
    expect(transport).toHaveBeenCalledTimes(2)
  })

  it('does not log out the user on a network failure', async () => {
    const client = new ApiClient(
      'https://unit.invalid',
      vi.fn<typeof fetch>().mockRejectedValue(new TypeError('offline')),
      () => 'csrf',
    )
    const listener = vi.fn()
    client.subscribe(listener)
    await expect(client.request('/resource')).rejects.toMatchObject({ status: 0 })
    expect(listener).not.toHaveBeenCalled()
  })

  it('drops late responses after logout or an account change', async () => {
    let finish: (response: Response) => void = () => {}
    const transport = vi.fn<typeof fetch>(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    const client = new ApiClient('https://unit.invalid', transport, () => 'csrf')
    const request = client.request('/private')
    client.sessionChanged('logout')
    finish(json(200, { private: 'old account' }))
    await expect(request).rejects.toMatchObject({ status: 401 })
  })

  it('formats 422 field errors without echoing rejected input', async () => {
    const transport = vi.fn<typeof fetch>().mockResolvedValue(
      json(422, {
        detail: [{ loc: ['body', 'email'], msg: 'Invalid email', input: 'private-input' }],
      }),
    )
    const client = new ApiClient('https://unit.invalid', transport)
    await expect(client.request('/resource')).rejects.toEqual(
      new ApiError(422, 'email: Invalid email'),
    )
  })

  it('does not expire a new login when an older refresh was waiting for the lock', async () => {
    let release: () => void = () => {}
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    const lock = async <T>(task: () => Promise<T>) => {
      await gate
      return task()
    }
    const transport = vi.fn<typeof fetch>().mockResolvedValue(json(401))
    const client = new ApiClient('https://unit.invalid', transport, () => 'csrf', lock)
    const events: string[] = []
    client.subscribe((event) => events.push(event))
    const oldRequest = client.request('/private')
    await Promise.resolve()
    client.sessionChanged('login')
    release()
    await expect(oldRequest).rejects.toMatchObject({ status: 401 })
    expect(events).toEqual(['login'])
  })

  it('refuses to rotate when the CSRF cookie is missing', async () => {
    const transport = vi.fn<typeof fetch>().mockResolvedValue(json(401))
    const client = new ApiClient('https://unit.invalid', transport, () => undefined)
    await expect(client.request('/private')).rejects.toMatchObject({ status: 401 })
    expect(transport.mock.calls.some(([url]) => String(url).endsWith('/auth/refresh'))).toBe(false)
  })
})
