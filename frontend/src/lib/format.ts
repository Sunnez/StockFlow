export const shortId = (id: string) => id.slice(0, 8).toUpperCase()
export const formatDate = (date: string) =>
  new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(date))
