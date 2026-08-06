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
    <section class="results-board mt-4">
        <div class="results-intro mb-4">
            <p class="text-muted mb-0">Review the results by extractor, then open details when you need metadata.</p>
        </div>

        <template v-if="hasNoResults">
            <div class="empty-state">
                <svg class="empty-state-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M800,575V800H200V575H75V825A100,100,0,0,0,175,925H825A100,100,0,0,0,925,825V575H800ZM650,450V150a75,75,0,0,0-75-75H425a75,75,0,0,0-75,75V450H200L350,598.981l110.858,110.1c21.365,21.22,56.919,21.22,78.284,0L650,598.981,800,450H650Z" transform="scale(.96)" fill="currentColor"/></svg>
                <p class="mb-0 text-muted">No triples found yet.</p>
            </div>
        </template>

        <div v-else class="results-stack">
            <div
                v-for="extractor in orderedExtractors"
                :key="extractor"
                class="results-stack-item"
            >
                <article :id="`results-panel-${extractor}`" class="extractor-panel h-100">
                    <header class="extractor-panel-header">
                        <div>
                            <p class="extractor-kicker mb-1">Extractor</p>
                            <h3 class="h5 mb-0">{{ formatExtractorName(extractor) }}</h3>
                        </div>

                        <span class="status-pill" :class="statusClass(extractor)">
                            {{ getExtractorStatusLabel(extractor) }}
                        </span>
                    </header>

                    <div class="extractor-stats">
                        <div class="stat-box">
                            <span class="stat-label">Triples</span>
                            <strong class="stat-value">{{ getTriplesCount(extractor) }}</strong>
                        </div>

                        <div class="stat-box">
                            <span class="stat-label">Time</span>
                            <strong class="stat-value">{{ formatTiming(extractor) }}</strong>
                        </div>
                    </div>

                    <div
                        v-if="extractorErrors[extractor]"
                        class="alert alert-warning mb-3"
                        role="alert"
                    >
                        {{ extractorErrors[extractor] }}
                    </div>

                    <div v-if="isExtractorProcessing(extractor)" class="extractor-placeholder">
                        <div class="spinner-border spinner-border-sm text-warning" role="status"></div>
                        <span>Processing triples...</span>
                    </div>

                    <div v-else-if="getTriplesCount(extractor) === 0" class="extractor-placeholder">
                        <svg class="icon-sm" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M892.285,819.383L666.631,593.728a310.794,310.794,0,0,0,58.05-181.388c0-172.5-139.839-312.34-312.341-312.34S100,239.838,100,412.34,239.838,724.681,412.34,724.681a310.918,310.918,0,0,0,181.4-58.05L819.383,892.275a25.053,25.053,0,0,0,35.342,0l37.56-37.55A25.071,25.071,0,0,0,892.285,819.383ZM412.34,624.732c-117.3,0-212.391-95.092-212.391-212.392S295.04,199.949,412.34,199.949,624.732,295.04,624.732,412.34,529.64,624.732,412.34,624.732Z" transform="scale(.96)" fill="currentColor"/></svg>
                        <span>No triples found.</span>
                    </div>

                    <div v-else class="triple-stack">
                        <section
                            v-for="group in getTripleGroups(extractor)"
                            :key="group.key"
                            class="triple-group"
                        >
                            <header
                                v-if="group.label"
                                class="triple-group-header"
                            >
                                <span class="triple-group-title">{{ group.label }}</span>
                                <span class="triple-group-count">{{ group.triples.length }}</span>
                            </header>

                            <div class="triple-group-list">
                                <TripleCard
                                    v-for="(triple, index) in group.triples"
                                    :key="getTripleKey(extractor, triple, index)"
                                    :triple="triple"
                                    :extractor="extractor"
                                    @focus-source-input="emit('focus-source-input', $event)"
                                />
                            </div>
                        </section>
                    </div>
                </article>
            </div>
        </div>
    </section>
</template>

<script setup>
/**
 * Displays extraction results grouped by extractor.
 * Each extractor panel shows a status badge, triple count, elapsed time,
 * and a list of TripleCards grouped by source input.
 */
import { computed } from 'vue'
import TripleCard from './TripleCard.vue'

const props = defineProps({
    triples:{
        type: Object,
        default: () => ({})
    },
    selectedExtractors: {
        type: Array,
        default: () => []
    },
    extractorErrors: {
        type: Object,
        default: () => ({})
    },
    extractorFinalTimes: {
        type: Object,
        default: () => ({})
    },
    extractorElapsedTimes: {
        type: Object,
        default: () => ({})
    },
    loadingByExtractor: {
        type: Object,
        default: () => ({})
    }
})
const emit = defineEmits(['focus-source-input'])

const orderedExtractors = computed(() => {
    const uniqueExtractors = [...new Set(props.selectedExtractors)]
    const extractorsWithResults = Object.keys(props.triples)
        .filter((extractor) => !uniqueExtractors.includes(extractor))

    return [...uniqueExtractors, ...extractorsWithResults]
})

const hasNoResults = computed(() => {
    if (!orderedExtractors.value.length) {
        return true
    }

    if (orderedExtractors.value.some((extractor) => isExtractorProcessing(extractor))) {
        return false
    }

    return orderedExtractors.value.every((extractor) => {
        return !props.extractorErrors[extractor] && (!props.triples[extractor] || props.triples[extractor].length === 0)
    })
})

/** Returns the extractor name uppercased for display. */
function formatExtractorName(extractor) {
    return extractor.toUpperCase()
}

/** Returns the elapsed time for an extractor: live counter while running, final value when done, '--' when idle. */
function formatTiming(extractor) {
    const finalTime = props.extractorFinalTimes[extractor]
    if (finalTime !== null && finalTime !== undefined) {
        return `${finalTime}s`
    }

    const elapsed = props.extractorElapsedTimes[extractor]
    if (elapsed !== null && elapsed !== undefined) {
        return `${elapsed}s`
    }

    return '--'
}

/** Returns true if the extractor is currently running. */
function isExtractorProcessing(extractor) {
    return props.loadingByExtractor[extractor] === true
}

/** Returns true if the extractor has a recorded final time (i.e. it has completed at least once). */
function isExtractorFinished(extractor) {
    return props.extractorFinalTimes[extractor] !== null && props.extractorFinalTimes[extractor] !== undefined
}

/** Returns the number of triples extracted by the given extractor. */
function getTriplesCount(extractor) {
    return Array.isArray(props.triples[extractor]) ? props.triples[extractor].length : 0
}

/** Returns the display label used to group a triple by its source input (file name or "Input N"). */
function getSourceGroupLabel(triple) {
    return triple?.sourceInputName
        || triple?.sourceInputLabel
        || (
            typeof triple?.sourceInputIndex === 'number'
                ? `Input ${triple.sourceInputIndex + 1}`
                : ''
        )
}

/**
 * Groups an extractor's triples by their source input label.
 * Returns an array of { key, label, triples } objects preserving insertion order.
 */
function getTripleGroups(extractor) {
    const extractorTriples = Array.isArray(props.triples[extractor]) ? props.triples[extractor] : []

    if (extractorTriples.length === 0) {
        return []
    }

    const groups = []
    const groupsMap = new Map()

    extractorTriples.forEach((triple, index) => {
        const label = getSourceGroupLabel(triple)
        const sourceIndex = typeof triple?.sourceInputIndex === 'number' ? triple.sourceInputIndex : 'unknown'
        const groupKey = `${sourceIndex}-${label || `group-${index}`}`
        const existingGroup = groupsMap.get(groupKey)

        if (existingGroup) {
            existingGroup.triples.push(triple)
            return
        }

        const nextGroup = {
            key: groupKey,
            label,
            triples: [triple],
        }

        groupsMap.set(groupKey, nextGroup)
        groups.push(nextGroup)
    })

    return groups
}

/**
 * Builds a stable Vue key for a TripleCard by hashing subject/predicate/object/date/source.
 * Falls back to an index-based key if no identity fields are present.
 */
function getTripleKey(extractor, triple, index) {
    const subject = triple?.subject?.id ?? triple?.subject?.qid ?? triple?.subject?.label ?? triple?.subject
    const predicate = triple?.predicate?.id ?? triple?.predicate?.pid ?? triple?.predicate?.label ?? triple?.predicate
    const obj = triple?.obj?.id ?? triple?.obj?.qid ?? triple?.obj?.label ?? triple?.obj
        ?? triple?.object?.id ?? triple?.object?.qid ?? triple?.object?.label ?? triple?.object
    const date = triple?.date ?? triple?.created_at ?? ''
    const sourceInput = triple?.sourceInputName ?? triple?.sourceInputLabel ?? triple?.sourceInputIndex ?? ''

    const identity = [subject, predicate, obj, date, sourceInput]
        .filter((value) => value !== null && value !== undefined && value !== '')
        .join('|')

    return identity ? `${extractor}-${identity}` : `${extractor}-fallback-${index}`
}

/** Returns a human-readable status label (Idle, Running, Completed, Error, Partial) for the extractor panel header. */
function getExtractorStatusLabel(extractor) {
    if (props.extractorErrors[extractor] && getTriplesCount(extractor) > 0) {
        return 'Partial'
    }

    if (props.extractorErrors[extractor]) {
        return 'Error'
    }

    if (isExtractorProcessing(extractor)) {
        return 'Running'
    }

    if (isExtractorFinished(extractor)) {
        return 'Completed'
    }

    return 'Idle'
}

/** Returns the CSS modifier class for the status pill based on the extractor's current state. */
function statusClass(extractor) {
    if (props.extractorErrors[extractor] && getTriplesCount(extractor) > 0) {
        return 'is-running'
    }

    if (props.extractorErrors[extractor]) {
        return 'is-error'
    }

    if (isExtractorProcessing(extractor)) {
        return 'is-running'
    }

    if (isExtractorFinished(extractor)) {
        return 'is-done'
    }

    return 'is-idle'
}
</script>

<style scoped>
.results-board,
.empty-state,
.empty-state-icon,
.extractor-panel,
.extractor-kicker,
.status-pill,
.stat-box,
.stat-label,
.stat-value,
.extractor-placeholder {
    --ods-orange-100: #ff7900;
    --ods-white-100: #fff;
    --ods-gray-200: #eee;
    --ods-gray-300: #ddd;
    --ods-gray-500: #999;
    --ods-gray-700: #595959;
    --ods-black-900: #000;
}

.results-board {
    margin-top: 1.5rem;
}

.results-intro {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.results-stack {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.results-stack-item {
    width: 100%;
}

.empty-state {
    min-height: 11.5rem;
    border: 0.05rem dashed var(--ods-gray-300);
    border-radius: 1rem;
    background: var(--ods-white-100);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
}

.empty-state-icon {
    width: 2rem;
    height: 2rem;
    color: var(--ods-gray-500);
}

.icon-sm {
    width: 1.5rem;
    height: 1.5rem;
}

.extractor-panel {
    border: 0.05rem solid var(--ods-gray-300);
    border-radius: 1rem;
    background: var(--ods-white-100);
    padding: 1.25rem;
    box-shadow: 0 1rem 2.5rem rgba(0, 0, 0, 0.05);
}

.extractor-panel-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1rem;
}

.extractor-kicker {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--ods-gray-700);
}

.status-pill {
    display: inline-flex;
    align-items: center;
    border-radius: 62.5rem;
    padding: 0.35rem 0.75rem;
    font-size: 0.75rem;
    font-weight: 700;
}

.status-pill.is-idle {
    background: var(--ods-gray-200);
    color: var(--ods-gray-700);
}

.status-pill.is-running {
    background: var(--ods-white-100);
    color: var(--ods-orange-100);
    border: 0.05rem solid var(--ods-orange-100);
}

.status-pill.is-done {
    background: var(--ods-orange-100);
    color: var(--ods-white-100);
    border: 0.05rem solid var(--ods-orange-100);
}

.status-pill.is-error {
    background: var(--ods-white-100);
    color: var(--ods-black-900);
    border: 0.05rem solid var(--ods-black-900);
}

.extractor-stats {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
    margin-bottom: 1rem;
}

.stat-box {
    border: 0.05rem solid var(--ods-gray-200);
    border-radius: 0.85rem;
    padding: 0.85rem 1rem;
    background: var(--ods-white-100);
}

.stat-label {
    display: block;
    font-size: 0.75rem;
    color: var(--ods-gray-700);
    margin-bottom: 0.25rem;
}

.stat-value {
    font-size: 1rem;
    color: var(--ods-black-900);
}

.extractor-placeholder {
    min-height: 10rem;
    border: 0.05rem dashed var(--ods-gray-300);
    border-radius: 1rem;
    background: var(--ods-white-100);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.65rem;
    color: var(--ods-gray-700);
}

.triple-stack {
    margin-top: 0.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.triple-group {
    border-radius: 1rem;
    background: #fafafa;
    border: 0.05rem solid var(--ods-gray-200);
    padding: 1rem;
}

.triple-group-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.65rem;
    border-bottom: 0.05rem solid var(--ods-gray-200);
}

.triple-group-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--ods-gray-700);
}

.triple-group-count {
    min-width: 1.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: 62.5rem;
    background: var(--ods-white-100);
    border: 0.05rem solid var(--ods-gray-200);
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--ods-gray-700);
    text-align: center;
}

.triple-group-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}
</style>
