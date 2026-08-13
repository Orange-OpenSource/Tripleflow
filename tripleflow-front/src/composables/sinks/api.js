import { buildErrorMessage, readJson } from '../apiError'
import { DEFAULT_API_BASE_URL } from '../extraction/constants'

const apiBaseUrl = (import.meta.env.VITE_TRIPLEFLOW_API_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')

/**
 * Fetches the publication targets registered on the backend.
 * Auth credentials are never part of the response; only `auth_type` is.
 * @returns {Promise<object[]>}
 */
export async function fetchSinks() {
    const response = await fetch(`${apiBaseUrl}/sinks`)
    if (!response.ok) {
        throw new Error(buildErrorMessage(await readJson(response), 'Failed to fetch targets'))
    }
    const data = await response.json()
    return data.sinks ?? data
}

/**
 * Registers a new SPARQL UPDATE target.
 * @param {object} config - target configuration (id, label, update_url, headers, body_format,
 *   auth, namespaces, knowledge_base, graph_uri, timeout_seconds)
 * @returns {Promise<object>}
 */
export async function createSink(config) {
    const response = await fetch(`${apiBaseUrl}/sinks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
    })
    if (!response.ok) {
        throw new Error(buildErrorMessage(await readJson(response), 'Failed to create the target'))
    }
    return response.json()
}

/**
 * Deletes a publication target by its identifier.
 * @param {string} id
 * @returns {Promise<void>}
 */
export async function deleteSink(id) {
    const response = await fetch(`${apiBaseUrl}/sinks/${encodeURIComponent(id)}`, {
        method: 'DELETE',
    })
    if (!response.ok) {
        throw new Error(buildErrorMessage(await readJson(response), 'Failed to delete the target'))
    }
}

/**
 * Publishes validated triples into a target's graph.
 * With dryRun, the backend builds and returns the SPARQL UPDATE without sending it.
 * @param {{ sinkId: string, tripleIds: string[], userName: string, dryRun?: boolean }} params
 * @returns {Promise<{ sink_id: string, dry_run: boolean, published_count: number, skipped: object[], sparql: string|null }>}
 */
export async function publishToSink({ sinkId, tripleIds, userName, dryRun = false }) {
    const response = await fetch(`${apiBaseUrl}/sinks/${encodeURIComponent(sinkId)}/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ triple_ids: tripleIds, user_name: userName, dry_run: dryRun }),
    })
    if (!response.ok) {
        throw new Error(buildErrorMessage(await readJson(response), 'Failed to publish the triples'))
    }
    return response.json()
}
