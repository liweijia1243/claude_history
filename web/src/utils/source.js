export const DEFAULT_SOURCE = 'claude'

function normalizePath(path = '') {
  return String(path).replace(/^\/+/, '')
}

export function sourceFromRoute(route) {
  return route?.params?.source || DEFAULT_SOURCE
}

export function apiPath(source, path) {
  const resolvedSource = source || DEFAULT_SOURCE
  const normalizedPath = normalizePath(path)
  return normalizedPath ? `/api/${resolvedSource}/${normalizedPath}` : `/api/${resolvedSource}`
}

export function routePath(source = DEFAULT_SOURCE, path) {
  const normalizedPath = normalizePath(path)

  if (!source || source === DEFAULT_SOURCE || normalizedPath === 'plans') {
    return normalizedPath ? `/${normalizedPath}` : '/'
  }

  return normalizedPath ? `/sources/${source}/${normalizedPath}` : `/sources/${source}`
}
