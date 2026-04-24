export function useLatestRequest() {
  let currentRequestId = 0

  function createRequest(snapshot = {}) {
    const id = ++currentRequestId

    return {
      snapshot,
      isCurrent(matches = () => true) {
        return id === currentRequestId && matches(snapshot)
      },
    }
  }

  function cancelRequests() {
    currentRequestId++
  }

  return {
    createRequest,
    cancelRequests,
  }
}
