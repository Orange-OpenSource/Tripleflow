/*  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

*/
import { DEFAULT_API_BASE_URL } from '../extraction/constants'

const apiBaseUrl = (import.meta.env.VITE_TRIPLEFLOW_API_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')

/**
 * Fetches the list of files available for validation from the backend.
 * @returns {Promise<object[]>}
 */
export async function fetchFiles() {
    const response = await fetch(`${apiBaseUrl}/files/`)
    if (!response.ok) throw new Error('Failed to fetch files')
    const data = await response.json()
    return data.files ?? data
}

/**
 * Fetches all triples associated with a specific file.
 * @param {string} fileId
 * @returns {Promise<object[]>}
 */
export async function fetchFileTriples(fileId) {
    const response = await fetch(`${apiBaseUrl}/files/${encodeURIComponent(fileId)}/triples`)
    if (!response.ok) throw new Error('Failed to fetch triples for this file')
    const data = await response.json()
    return data.triples ?? data
}

/**
 * Fetches all triples from the backend (used when no file filter is active).
 * @returns {Promise<object[]>}
 */
export async function fetchTriples() {
    const response = await fetch(`${apiBaseUrl}/triples/`)
    if (!response.ok) throw new Error('Failed to fetch triples from the API')
    const data = await response.json()
    return data.triples ?? data
}

/**
 * Fetches the raw text content of a stored file.
 * @param {string} fileId
 * @returns {Promise<string>}
 */
export async function fetchFileContent(fileId) {
    const response = await fetch(`${apiBaseUrl}/files/${encodeURIComponent(fileId)}/content`)
    if (!response.ok) throw new Error('Failed to fetch file content')
    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
        const data = await response.json()
        return data.content ?? data.text ?? JSON.stringify(data, null, 2)
    }
    return response.text()
}

/**
 * Renames a file in the backend.
 * @param {string} fileId
 * @param {string} fileName
 * @returns {Promise<object>}
 */
export async function renameFile(fileId, fileName) {
    const response = await fetch(`${apiBaseUrl}/files/${encodeURIComponent(fileId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_name: fileName }),
    })
    if (!response.ok) throw new Error('Failed to rename file')
    return response.json()
}

/**
 * Clears all review data (files and triples) from the backend, keeping extractor configs.
 * @param {string} userName - reviewer performing the reset, recorded in the audit log
 * @returns {Promise<{ message: string, triples_deleted: number, files_deleted: number }>}
 */
export async function clearDatabase(userName) {
    const response = await fetch(`${apiBaseUrl}/database?user_name=${encodeURIComponent(userName)}`, {
        method: 'DELETE',
    })
    if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.detail || 'Failed to clear the database')
    }
    return response.json()
}

/**
 * Deletes a single file and all of its triples from the backend.
 * @param {string} fileId
 * @param {string} userName - reviewer performing the deletion, recorded in the audit log
 * @returns {Promise<{ message: string, file_id: string, triples_deleted: number }>}
 */
export async function deleteFile(fileId, userName) {
    const url = `${apiBaseUrl}/files/${encodeURIComponent(fileId)}?user_name=${encodeURIComponent(userName)}`
    const response = await fetch(url, { method: 'DELETE' })
    if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.detail || 'Failed to delete the file')
    }
    return response.json()
}

/**
 * Submits a reviewer's decision for a triple (approved / rejected / modified).
 * Sends a PATCH to /triples/validate and throws an Error with a readable message on failure.
 * @param {{ triple_id: string, status: string, user_id: string, user_name: string, comment?: string, modified_triple?: object }} params
 * @returns {Promise<object>}
 */
export async function submitValidation({ triple_id, status, user_id, user_name, comment, modified_triple }) {
    const body = { triple_id, status, user_id, user_name, comment }
    if (modified_triple !== undefined) body.modified_triple = modified_triple
    const response = await fetch(`${apiBaseUrl}/triples/validate`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })

    if (!response.ok) {
        const data = await response.json().catch(() => null)
        const detail = data?.detail
        const message = typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
                ? detail.map(d => {
                    const loc = Array.isArray(d?.loc) ? d.loc.join('.') : ''
                    const msg = d?.msg || JSON.stringify(d)
                    return loc ? `${loc}: ${msg}` : msg
                }).join(' | ')
                : 'Failed to submit validation'
        throw new Error(message)
    }

    return response.json()
}
