/*  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

*/
import { isNullLikeEntityValue } from '../entity.js'

/**
 * Coerces a value to a finite number, or returns null if the value is not numeric.
 * @param {*} value
 * @returns {number|null}
 */
export function normalizeScore(value) {
    if (typeof value === 'number' && Number.isFinite(value)) {
        return value
    }

    if (typeof value === 'string') {
        const parsed = Number(value)
        if (Number.isFinite(parsed)) {
            return parsed
        }
    }

    return null
}

/**
 * Coerces a value to a non-negative integer, or returns null if invalid.
 * @param {*} value
 * @returns {number|null}
 */
function normalizeInputIndex(value) {
    if (typeof value === 'number' && Number.isInteger(value) && value >= 0) {
        return value
    }

    if (typeof value === 'string' && value.trim() !== '') {
        const parsed = Number(value)
        if (Number.isInteger(parsed) && parsed >= 0) {
            return parsed
        }
    }

    return null
}

/**
 * Looks up a source object by index in the inputSources array.
 * Returns null if the array is missing or the index is invalid.
 * @param {Array} inputSources
 * @param {number|null} inputIndex
 * @returns {object|null}
 */
function buildInputSource(inputSources, inputIndex) {
    if (!Array.isArray(inputSources) || inputIndex === null || inputIndex < 0) {
        return null
    }

    return inputSources[inputIndex] ?? null
}

/**
 * Returns a usable timestamp string from mixed date formats.
 * Empty strings and invalid Date objects are treated as missing.
 * @param {*} value
 * @returns {string|null}
 */
function normalizeTimestampValue(value) {
    if (value === null || value === undefined) {
        return null
    }

    if (typeof value === 'string') {
        const trimmed = value.trim()
        return trimmed !== '' ? trimmed : null
    }

    if (typeof value === 'number' && Number.isFinite(value)) {
        return String(value)
    }

    if (value instanceof Date && !Number.isNaN(value.getTime())) {
        return value.toISOString()
    }

    return null
}

/**
 * Returns the first non-empty timestamp candidate.
 * @param {...*} candidates
 * @returns {string|null}
 */
function pickFirstTimestamp(...candidates) {
    for (const candidate of candidates) {
        const normalized = normalizeTimestampValue(candidate)
        if (normalized !== null) {
            return normalized
        }
    }

    return null
}

/**
 * Returns a cleaned string value, or an empty string for null-like placeholders.
 * @param {*} value
 * @returns {string}
 */
function sanitizeEntityString(value) {
    if (isNullLikeEntityValue(value)) {
        return ''
    }

    return typeof value === 'string' ? value.trim() : String(value)
}

/**
 * Normalizes an entity object/string so IDs and labels are consistent.
 * @param {*} part
 * @param {'item'|'property'} type
 * @returns {{ id?: string, qid?: string, pid?: string, label?: string }|null|*}
 */
function normalizeEntityPart(part, type) {
    if (part === null || part === undefined) {
        return part
    }

    if (typeof part !== 'object') {
        const label = sanitizeEntityString(part)
        return label ? { label } : null
    }

    const id = sanitizeEntityString(part.id)
    const qid = sanitizeEntityString(part.qid)
    const pid = sanitizeEntityString(part.pid)
    const label = sanitizeEntityString(part.label)

    const normalizedId = sanitizeEntityString(
        type === 'property'
            ? (pid || id)
            : (qid || id)
    )

    const normalizedPart = {
        ...part,
        id: normalizedId,
        qid: type === 'item' ? normalizedId : qid,
        pid: type === 'property' ? normalizedId : pid,
        label,
    }

    return normalizedPart
}

/**
 * Normalizes a raw triple object from the API: standardizes field names,
 * resolves entity IDs, reads the heuristic score, and attaches source input metadata.
 * @param {object} triple - raw triple from the API
 * @param {Array|null} inputSources - list of source descriptors for this extraction run
 * @param {number|null} fallbackIndex - index to use when the triple has no input_index
 * @returns {object}
 */
function normalizeTriple(triple, inputSources = null, fallbackIndex = null) {
    if (!triple || typeof triple !== 'object') {
        return triple
    }

    const heuristicScore = normalizeScore(triple.heuristic_score)
    const sourceInputIndex = normalizeInputIndex(
        triple.input_index
        ?? triple.inputIndex
        ?? triple.source_input_index
        ?? fallbackIndex
    )
    const resolvedInputSource = sourceInputIndex !== null
        ? buildInputSource(inputSources, sourceInputIndex)
        : (Array.isArray(inputSources) && inputSources.length === 1 ? inputSources[0] : null)

    const rawObj = triple.obj ?? triple.object ?? null
    const normalizedSubject = normalizeEntityPart(triple.subject, 'item')
    const normalizedPredicate = normalizeEntityPart(triple.predicate, 'property')
    const normalizedObj = normalizeEntityPart(rawObj, 'item')

    const normalizedDate = pickFirstTimestamp(
        triple.date,
        triple.created_at,
        triple.timestamp,
        triple.extraction_date,
        triple.generated_at,
        triple.createdAt,
        triple.extractionDate
    )

    return {
        ...triple,
        subject: normalizedSubject,
        predicate: normalizedPredicate,
        obj: normalizedObj,
        object: normalizedObj,
        date: normalizedDate,
        created_at: normalizedDate,
        heuristic_score: heuristicScore,
        sourceInputIndex,
        sourceInputLabel: triple.source_input_label
            ?? triple.sourceInputLabel
            ?? resolvedInputSource?.label
            ?? (sourceInputIndex !== null ? `Input ${sourceInputIndex + 1}` : ''),
        sourceInputName: triple.source_input_name
            ?? triple.sourceInputName
            ?? resolvedInputSource?.name
            ?? '',
        sourceInputType: triple.source_input_type
            ?? triple.sourceInputType
            ?? resolvedInputSource?.type
            ?? '',
    }
}

/**
 * Flattens and normalizes triples from a batch API response (result.items array).
 * Each item may contain its own triples list and an optional index.
 * @param {Array} items
 * @param {Array} inputSources
 * @returns {object[]}
 */
function extractTriplesFromItems(items, inputSources) {
    return items.flatMap((item, itemIndex) => {
        const itemTriples = item?.triples ?? item?.result?.triples ?? item?.result
        const triplesList = Array.isArray(itemTriples) ? itemTriples : []
        const normalizedItemIndex = normalizeInputIndex(item?.index ?? itemIndex)

        return triplesList.map((triple) => normalizeTriple(triple, inputSources, normalizedItemIndex))
    })
}

/**
 * Normalizes all triples in an API response, handling both batch (items) and single-run formats.
 * Attaches the heuristic score and source input metadata to each triple.
 * @param {object} data - raw API response body
 * @param {{ inputSources?: Array }} options
 * @returns {object[]}
 */
export function normalizeTriples(data, options = {}) {
    const inputSources = Array.isArray(options.inputSources) ? options.inputSources : []
    const extractionTimestamp = normalizeTimestampValue(options.extractionTimestamp)
    const items = Array.isArray(data?.result?.items) ? data.result.items : []

    if (items.length > 0) {
        return extractTriplesFromItems(items, inputSources).map((triple) => ({
            ...triple,
            date: pickFirstTimestamp(extractionTimestamp, triple.date, triple.created_at),
            created_at: pickFirstTimestamp(extractionTimestamp, triple.created_at, triple.date),
        }))
    }

    const extractedTriples = data?.result?.triples ?? data?.result
    const triplesList = Array.isArray(extractedTriples) ? extractedTriples : []

    return triplesList.map((triple) => {
        const normalizedTriple = normalizeTriple(triple, inputSources, null)
        const timestamp = pickFirstTimestamp(extractionTimestamp, normalizedTriple.date, normalizedTriple.created_at)

        return {
            ...normalizedTriple,
            date: timestamp,
            created_at: timestamp,
        }
    })
}
