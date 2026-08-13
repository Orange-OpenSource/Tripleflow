/**
 * Builds a readable error message from a FastAPI/HTTP error body.
 * Handles plain strings, a `detail` string, and FastAPI validation `detail` arrays.
 * @param {*} data
 * @param {string} fallback
 * @returns {string}
 */
export function buildErrorMessage(data, fallback) {
    const detail = data?.detail ?? data?.message ?? data?.error

    if (typeof detail === 'string' && detail.trim()) {
        return detail
    }

    if (Array.isArray(detail)) {
        const messages = detail
            .map((item) => {
                if (!item || typeof item !== 'object') {
                    return typeof item === 'string' ? item : null
                }
                const location = Array.isArray(item.loc) ? item.loc.join('.') : ''
                const message = item.msg || item.message || JSON.stringify(item)
                return location ? `${location}: ${message}` : message
            })
            .filter(Boolean)

        if (messages.length > 0) {
            return messages.join(' | ')
        }
    }

    return fallback
}

/** Reads a JSON body, tolerating empty/non-JSON responses. */
export async function readJson(response) {
    return response.json().catch(() => null)
}
