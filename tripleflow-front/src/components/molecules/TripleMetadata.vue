<!--  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

-->

<template>
    <div class="mt-3">
        <ul class="list-unstyled mb-0">
            <li>
                <strong>Subject ID:</strong>
                <a
                    v-if="subjectLink"
                    :href="subjectLink"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    {{ subjectId }}
                </a>
                <span v-else>{{ subjectId }}</span>
            </li>
            <li>
                <strong>Predicate ID:</strong>
                <a
                    v-if="predicateLink"
                    :href="predicateLink"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    {{ predicateId }}
                </a>
                <span v-else>{{ predicateId }}</span>
            </li>
            <li>
                <strong>Object ID:</strong>
                <a
                    v-if="objLink"
                    :href="objLink"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    {{ objId }}
                </a>
                <span v-else>{{ objId }}</span>
            </li>
            <li><strong>Timestamp:</strong> {{ dateValue }}</li>
            <li v-if="sourceInputValue"><strong>Input:</strong> {{ sourceInputValue }}</li>
            <li v-if="sourceValue"><strong>Source:</strong> {{ sourceValue }}</li>
            <li><strong>Score:</strong> {{ scoreValue }}</li>
        </ul>
    </div>
</template>

<script setup>
/**
 * Displays detailed metadata for a single triple:
 * subject/predicate/object IDs (linked to the extractor's knowledge base when valid), date, source input, and heuristic score.
 */
import { computed } from 'vue'
import { isNullLikeEntityValue, ENTITY_PLACEHOLDER } from '../../composables/entity.js'
import { buildEntityLink } from '../../composables/entityLinks.js'

const props = defineProps({
    triple: {
        type: Object,
        required: true,
    },
    extractor: {
        type: String,
        default: '',
    },
})

function normalizeEntityId(value) {
    if (isNullLikeEntityValue(value)) {
        return ENTITY_PLACEHOLDER
    }

    return String(value).trim()
}

const subjectId = computed(() => {
    return normalizeEntityId(props.triple?.subject?.qid ?? props.triple?.subject?.id)
})

const predicateId = computed(() => {
    return normalizeEntityId(props.triple?.predicate?.pid ?? props.triple?.predicate?.id)
})

const objId = computed(() => {
    return normalizeEntityId(props.triple?.obj?.qid ?? props.triple?.obj?.id ?? props.triple?.object?.qid ?? props.triple?.object?.id)
})

const subjectLink = computed(() => buildEntityLink(subjectId.value, 'item', props.extractor))
const predicateLink = computed(() => buildEntityLink(predicateId.value, 'property', props.extractor))
const objLink = computed(() => buildEntityLink(objId.value, 'item', props.extractor))

const dateValue = computed(() => {
    const raw = props.triple?.date ?? props.triple?.created_at ?? props.triple?.timestamp ?? props.triple?.extraction_date
    if (!raw) return '-'

    const parsed = new Date(raw)
    if (isNaN(parsed.getTime())) return raw

    return new Intl.DateTimeFormat('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    }).format(parsed)
})

const sourceInputValue = computed(() => {
    return props.triple?.sourceInputLabel
        || props.triple?.sourceInputName
        || (
            typeof props.triple?.sourceInputIndex === 'number'
                ? `Input ${props.triple.sourceInputIndex + 1}`
                : ''
        )
})

const sourceValue = computed(() => {
    return props.triple?.source || props.extractor || ''
})

/** Coerces a raw score field to a finite number, or null when absent/invalid. */
function toFiniteScore(raw) {
    const value = typeof raw === 'string' ? Number(raw) : raw
    return typeof value === 'number' && Number.isFinite(value) ? value : null
}

const scoreValue = computed(() => {
    const heuristic = toFiniteScore(props.triple?.heuristic_score)
    if (heuristic != null) {
        return heuristic.toFixed(2)
    }

    // No score at all (abnormal): match the validation table's em dash.
    return '—'
})
</script>
