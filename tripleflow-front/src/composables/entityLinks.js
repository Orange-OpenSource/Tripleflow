/*  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

*/
/**
 * Routes an entity/property link to the knowledge base declared by the extractor
 * that produced the triple. One uniform rule for every extractor (built-in or custom),
 * driven entirely by the `knowledge_base` config served by the backend:
 *   - "wikidata"           -> links to public wikidata.org
 *   - "wikibase" + baseUrl -> links to that Wikibase instance (Item:/Property: pages)
 *   - anything else (unknown extractor, no config, missing base URL) -> no link at all:
 *     without a declared alignment we cannot know which knowledge base a QID belongs to.
 * Anything that is not a valid Q###/P### id also yields no link, so callers can hide it.
 *
 * `buildSinkEntityLink` applies the same rule to a publication target's own
 * `knowledge_base`, so an already-published triple links to where it landed.
 */
import { useExtractors } from './extractors/useExtractors'
import { useSinks } from './sinks/useSinks'

/** Base URL of public Wikidata used to build item/property links. */
export const WIKIDATA_BASE_URL = 'https://www.wikidata.org/wiki/'

/**
 * Returns a public Wikidata URL for a given entity ID and type. Wikidata keeps items in the
 * main namespace (no prefix) and properties under the Property: namespace.
 * @param {string} id - entity ID (Q### for items, P### for properties)
 * @param {'item'|'property'} entityType
 * @returns {string}
 */
export function buildWikidataLink(id, entityType) {
    if (typeof id !== 'string') {
        return ''
    }

    const normalizedId = id.trim().toUpperCase()

    if (entityType === 'item' && /^Q\d+$/.test(normalizedId)) {
        return `${WIKIDATA_BASE_URL}${normalizedId}`
    }

    if (entityType === 'property' && /^P\d+$/.test(normalizedId)) {
        return `${WIKIDATA_BASE_URL}Property:${normalizedId}`
    }

    return ''
}

/**
 * Returns a link to a generic Wikibase instance, which exposes items under
 * the Item: namespace and properties under Property:.
 * @param {string} id - entity ID (Q### for items, P### for properties)
 * @param {'item'|'property'} entityType
 * @param {string} baseUrl - wiki base URL, e.g. "https://example.org/wiki/"
 * @returns {string}
 */
export function buildWikibaseLink(id, entityType, baseUrl) {
    if (typeof id !== 'string' || typeof baseUrl !== 'string' || baseUrl.trim() === '') {
        return ''
    }

    const normalizedId = id.trim().toUpperCase()
    const base = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`

    if (entityType === 'item' && /^Q\d+$/.test(normalizedId)) {
        return `${base}Item:${normalizedId}`
    }

    if (entityType === 'property' && /^P\d+$/.test(normalizedId)) {
        return `${base}Property:${normalizedId}`
    }

    return ''
}

/**
 * Normalises a `knowledge_base` block (from an extractor or from a publication
 * target) into the linking base to use. Returns null when no alignment is
 * declared — no config, type "none", or a wikibase without base URL: in that
 * case no link must be produced, since a QID alone does not say which knowledge
 * base it belongs to.
 * @param {object} [kb]
 * @returns {{ type: 'wikidata' } | { type: 'wikibase', baseUrl: string } | null}
 */
function normalizeLinkingBase(kb) {
    if (kb?.type === 'wikidata') {
        return { type: 'wikidata' }
    }

    if (kb && (kb.type === 'wikibase' || kb.type === 'custom')) {
        const baseUrl = kb.base_url ?? kb.baseUrl
        if (typeof baseUrl === 'string' && baseUrl.trim() !== '') {
            return { type: 'wikibase', baseUrl: baseUrl.trim() }
        }
    }

    return null
}

/** Builds the URL for an ID against an already-resolved linking base. */
function linkForBase(base, id, entityType) {
    if (!base) {
        return ''
    }

    return base.type === 'wikibase'
        ? buildWikibaseLink(id, entityType, base.baseUrl)
        : buildWikidataLink(id, entityType)
}

/**
 * Resolves the linking base declared in an extractor's `knowledge_base` config.
 * @param {string} extractorName
 * @returns {{ type: 'wikidata' } | { type: 'wikibase', baseUrl: string } | null}
 */
function resolveLinkingBase(extractorName) {
    const name = typeof extractorName === 'string' ? extractorName.trim().toLowerCase() : ''

    if (!name) {
        return null
    }

    const { availableExtractors } = useExtractors()
    const match = availableExtractors.value.find((extractor) => extractor.id === name)
    return normalizeLinkingBase(match?.knowledge_base ?? match?.knowledgeBase)
}

/**
 * Builds a link for a triple part, targeting the knowledge base configured for the extractor
 * that produced it. Returns an empty string when no alignment is declared or the ID is not
 * a valid Q###/P### identifier.
 * @param {string} id - entity ID (Q### for items, P### for properties)
 * @param {'item'|'property'} entityType
 * @param {string} [extractorName] - name of the extractor that produced the triple
 * @returns {string}
 */
export function buildEntityLink(id, entityType, extractorName) {
    return linkForBase(resolveLinkingBase(extractorName), id, entityType)
}

/**
 * Builds a link for a triple part into the knowledge base a publication target
 * writes to — the other end of the loop from `buildEntityLink`: once a triple has
 * been published, its identifiers point at where they now live rather than at the
 * extractor's reference base.
 *
 * Returns an empty string when the target declares no browsable base, is unknown,
 * or the targets have not been loaded yet, so callers can fall back to the
 * extractor's link.
 * @param {string} id - entity ID (Q### for items, P### for properties)
 * @param {'item'|'property'} entityType
 * @param {string} [sinkId] - id of the target the triple was published to
 * @returns {string}
 */
export function buildSinkEntityLink(id, entityType, sinkId) {
    const targetId = typeof sinkId === 'string' ? sinkId.trim() : ''

    if (!targetId) {
        return ''
    }

    const { availableSinks } = useSinks()
    const match = availableSinks.value.find((sink) => sink.id === targetId)

    return linkForBase(normalizeLinkingBase(match?.knowledge_base ?? match?.knowledgeBase), id, entityType)
}
