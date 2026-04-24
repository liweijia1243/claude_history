export const DEFAULT_SOURCE = 'claude'

function normalizePath(path = '') {
  return String(path).replace(/^\/+/, '')
}

export function sourceFromRoute(route) {
  return route?.params?.source || DEFAULT_SOURCE
}

export function apiPath(source, path) {
  const normalizedPath = normalizePath(path)
  return normalizedPath ? `/api/${source}/${normalizedPath}` : `/api/${source}`
}

export function routePath(source = DEFAULT_SOURCE, path) {
  const normalizedPath = normalizePath(path)

  if (!source || source === DEFAULT_SOURCE) {
    return normalizedPath ? `/${normalizedPath}` : '/'
  }

  return normalizedPath ? `/sources/${source}/${normalizedPath}` : `/sources/${source}`
}
