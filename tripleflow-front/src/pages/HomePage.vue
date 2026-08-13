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
    <main class="app-content page-shell">
        <section
            class="top-layout"
            :class="{ 'is-resizing': isResizingPanel }"
            :style="layoutStyle"
        >
            <aside class="control-panel">
                <div class="page-intro">
                    <p class="eyebrow mb-2">Triple Extraction Workspace</p>
                    <h1 class="mb-2">TripleFlow</h1>
                    <p class="page-subtitle mb-0">
                        Upload your sources, launch one or more extractors, then review the triples.
                    </p>
                </div>

                <div class="control-card">
                    <h2 class="h4 mb-3">Extraction Setup</h2>
                    <ExtractionForm
                        v-model="text"
                        :fileTextInputs="fileTextInputs"
                        :extractors="selectedExtractors"
                        :extractorOptions="extractorOptions"
                        :highlightedInputIndex="highlightedInputIndex"
                        @update:extractors="updateExtractors"
                        :files="selectedFiles"
                        :fileName="selectedFileName"
                        :parsingEnabled="parsingEnabled"
                        :chunkingEnabled="chunkingEnabled"
                        :chunkSize="chunkSize"
                        :chunkOverlap="chunkOverlap"
                        @update:file="handleFileUpload"
                        @update:file-text="handleFileTextUpdate"
                        @update:input-name="handleInputNameUpdate"
                        @remove:file="removeFile"
                        @add:manual-input="addManualInput"
                        @convert:to-manual="convertToManualInput"
                        @clear:text="clearText"
                        @update:parsing-enabled="setParsingEnabled"
                        @update:chunking-enabled="chunkingEnabled = $event"
                        @update:chunk-size="chunkSize = $event"
                        @update:chunk-overlap="chunkOverlap = $event"
                        :disabled="isLoading || isParsing"
                        @submit="runExtraction"
                    />
                </div>
            </aside>

            <button
                type="button"
                class="panel-resizer"
                aria-label="Resize extraction panel"
                @mousedown="startPanelResize"
            ></button>

            <div class="content-column">
                <div class="workspace-steps" aria-label="Extraction steps">
                    <span class="step-item is-done">
                        <span class="step-number">1</span>
                        <span>Configuration</span>
                    </span>
                    <span class="step-divider" aria-hidden="true">/</span>
                    <span class="step-item" :class="{ 'is-active': isLoading, 'is-done': hasExtractionFinished }">
                        <span class="step-number">2</span>
                        <span>Extraction</span>
                    </span>
                    <span class="step-divider" aria-hidden="true">/</span>
                    <span class="step-item" :class="{ 'is-active': hasResultsStepActive }">
                        <span class="step-number">3</span>
                        <span>Results</span>
                    </span>
                </div>

                <div class="workflow-panel">
                    <Workflow />
                </div>

                <section v-if="isParsing" class="parsing-section" aria-live="polite">
                    <div class="parsing-card">
                        <div class="spinner-border parsing-spinner" role="status">
                            <span class="visually-hidden">Parsing in progress</span>
                        </div>
                        <div class="parsing-body">
                            <p class="parsing-title mb-1">{{ parsingTitle }}</p>
                            <p class="parsing-detail mb-0">{{ parsingDetail }}</p>
                        </div>
                    </div>
                </section>

                <section
                    v-if="hasExtractionActivity || errorMessage || isLoading"
                    class="results-section"
                >
                    <div class="results-card">
                        <div class="results-header mb-3">
                            <div>
                                <p class="eyebrow mb-2">Step 3</p>
                                <h2 class="h4 mb-1">Results</h2>
                                <p class="text-muted mb-0">Compare extractor outputs and inspect triple details.</p>
                            </div>
                        </div>

                        <div v-if="errorMessage" class="alert alert-danger" role="alert">
                            {{ errorMessage }}
                        </div>

                        <p v-else-if="isLoading && Object.keys(triples).length === 0" class="text-muted">In progress...</p>

                        <TripleResultsList
                            v-if="hasExtractionActivity"
                            :triples="triples"
                            :selectedExtractors="selectedExtractors"
                            :extractorErrors="extractorErrors"
                            :extractorFinalTimes="extractorFinalTimes"
                            :extractorElapsedTimes="extractorElapsedTimes"
                            :loadingByExtractor="loadingByExtractor"
                            @focus-source-input="focusSourceInput"
                        />

                        <div v-if="hasExtractionFinished && !errorMessage" class="validate-cta">
                            <p class="validate-hint">
                                Extracted triples are saved in MongoDB with status <strong>pending</strong>.
                            </p>
                            <button class="btn-validate-cta" @click="$emit('navigate', 'validation')">
                                Review &amp; validate triples →
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        </section>
    </main>
</template>


<script setup>
/**
 * Main extraction workspace page.
 * Shows ExtractionForm in a resizable left panel and the Workflow + TripleResultsList on the right.
 * Clicking a triple card scrolls to and highlights the corresponding source input.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import ExtractionForm from '../components/molecules/ExtractionForm.vue'
import TripleResultsList from '../components/organisms/TripleResultsList.vue'
import Workflow from '../components/organisms/Workflow.vue'
import { useExtractionState } from '../composables/UseExtractionState'
import { useExtractors } from '../composables/extractors/useExtractors'

const emit = defineEmits(['navigate'])

const { extractorOptions, loadExtractors } = useExtractors()

const {
    text,
    fileTextInputs,
    selectedFiles,
    selectedExtractors,
    selectedFileName,
    parsingEnabled,
    setParsingEnabled,
    isParsing,
    parsingProgress,
    chunkingEnabled,
    chunkSize,
    chunkOverlap,
    loadingByExtractor,
    extractorElapsedTimes,
    extractorFinalTimes,
    extractorErrors,
    isLoading,
    errorMessage,
    triples,
    updateExtractors,
    handleFileUpload,
    addManualInput,
    convertToManualInput,
    clearText,
    updateFileText,
    updateInputName,
    removeFile,
    runExtraction,
} = useExtractionState()

// Docling runs on the backend and can take several seconds on the first document
// (models are loaded lazily), so the step gets its own spinner above the results.
const parsingTitle = computed(() => (
    parsingEnabled.value ? 'Parsing documents with Docling...' : 'Reading files...'
))

const parsingDetail = computed(() => {
    const { current, total, name } = parsingProgress.value

    if (total === 0) {
        return ''
    }

    const position = total > 1 ? `${current}/${total} — ` : ''
    return `${position}${name}`
})

const hasExtractionActivity = computed(() => {
    return Object.keys(loadingByExtractor.value).length > 0
        || Object.keys(triples.value).length > 0
        || Object.keys(extractorErrors.value).length > 0
        || Object.keys(extractorFinalTimes.value).length > 0
})

const hasExtractionFinished = computed(() => {
    return !isLoading.value && (
        Object.keys(triples.value).length > 0
        || Object.keys(extractorErrors.value).length > 0
        || Object.keys(extractorFinalTimes.value).length > 0
    )
})

const hasResultsStepActive = computed(() => {
    return hasExtractionFinished.value
})

const minPanelWidth = 320
const maxPanelWidth = 620
const defaultPanelWidth = maxPanelWidth
const panelWidth = ref(defaultPanelWidth)
const isResizingPanel = ref(false)
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1440)
const resizerWidth = 8
const compactBreakpoint = 992
const highlightedInputIndex = ref(null)
let highlightResetTimerId = null

function pixelsToRem(value) {
    return `${value / 16}rem`
}

/** Forwards a file text update from ExtractionForm to the extraction state composable. */
function handleFileTextUpdate({ index, value }) {
    updateFileText(index, value)
}

/** Forwards a manual input name update from ExtractionForm to the extraction state composable. */
function handleInputNameUpdate({ index, name }) {
    updateInputName(index, name)
}

/**
 * Highlights and scrolls to the source input block at the given index.
 * Clears the highlight after 1.3s.
 * @param {number} inputIndex
 */
async function focusSourceInput(inputIndex) {
    if (typeof inputIndex !== 'number' || inputIndex < 0) {
        return
    }

    highlightedInputIndex.value = inputIndex
    await nextTick()

    const targetElement = document.querySelector(`[data-input-index="${inputIndex}"]`)
    targetElement?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
    })

    if (highlightResetTimerId) {
        clearTimeout(highlightResetTimerId)
    }

    highlightResetTimerId = window.setTimeout(() => {
        highlightedInputIndex.value = null
        highlightResetTimerId = null
    }, 1300)
}

const layoutStyle = computed(() => {
    if (viewportWidth.value < compactBreakpoint) {
        return {}
    }

    return {
        gridTemplateColumns: `${pixelsToRem(panelWidth.value)} ${pixelsToRem(resizerWidth)} minmax(0, 1fr)`
    }
})

/** Clamps a panel width value between minPanelWidth and an upper bound that also depends on the window width. */
function clampPanelWidth(width) {
    const maxWidth = typeof window === 'undefined'
        ? maxPanelWidth
        : Math.min(maxPanelWidth, Math.max(minPanelWidth, window.innerWidth - 520))

    return Math.min(Math.max(width, minPanelWidth), maxWidth)
}

/** Starts a panel resize drag and sets the initial width from the cursor position. */
function startPanelResize(event) {
    isResizingPanel.value = true
    panelWidth.value = clampPanelWidth(event.clientX)
    document.body.classList.add('is-resizing-extraction-panel')
}

/** Updates the panel width while a resize drag is in progress. */
function resizePanel(event) {
    if (!isResizingPanel.value) {
        return
    }

    panelWidth.value = clampPanelWidth(event.clientX)
}

/** Ends a resize drag and removes the resize cursor from the body. */
function stopPanelResize() {
    if (!isResizingPanel.value) {
        return
    }

    isResizingPanel.value = false
    document.body.classList.remove('is-resizing-extraction-panel')
}

/** Updates the tracked viewport width on window resize and re-clamps the panel width. */
function updateViewportWidth() {
    if (typeof window === 'undefined') {
        return
    }

    viewportWidth.value = window.innerWidth
    panelWidth.value = clampPanelWidth(panelWidth.value)
    stopPanelResize()
}

onMounted(() => {
    loadExtractors()

    if (typeof window === 'undefined') {
        return
    }

    panelWidth.value = clampPanelWidth(panelWidth.value)
    window.addEventListener('mousemove', resizePanel)
    window.addEventListener('mouseup', stopPanelResize)
    window.addEventListener('resize', updateViewportWidth)
})

onBeforeUnmount(() => {
    if (typeof window === 'undefined') {
        return
    }

    window.removeEventListener('mousemove', resizePanel)
    window.removeEventListener('mouseup', stopPanelResize)
    window.removeEventListener('resize', updateViewportWidth)
    document.body.classList.remove('is-resizing-extraction-panel')

    if (highlightResetTimerId) {
        clearTimeout(highlightResetTimerId)
        highlightResetTimerId = null
    }
})
</script>

<style scoped>
.page-shell,
.page-intro,
.eyebrow,
.page-subtitle,
.control-panel,
.panel-resizer,
.workspace-steps,
.step-number,
.step-divider,
.control-card,
.results-card {
    --ods-orange-100: #ff7900;
    --ods-white-100: #fff;
    --ods-gray-200: #eee;
    --ods-gray-300: #ddd;
    --ods-gray-400: #ccc;
    --ods-gray-500: #999;
    --ods-gray-700: #595959;
    --ods-gray-800: #333;
    --ods-black-900: #000;
}

.page-shell {
    width: 100%;
    min-height: calc(100vh - 5rem);
    background: var(--ods-white-100);
}

.page-intro {
    padding: 2rem 1.5rem 1.5rem;
    border-bottom: 0.1rem solid var(--ods-gray-300);
}

.eyebrow {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--ods-gray-700);
    font-weight: 700;
}

.page-subtitle {
    max-width: 34rem;
    color: var(--ods-gray-700);
}

.top-layout {
    display: grid;
    grid-template-columns: 27rem 0.5rem minmax(0, 1fr);
    grid-template-areas: 'controls resizer workflow';
    align-items: start;
    min-height: inherit;
}

:global(body.is-resizing-extraction-panel) {
    cursor: col-resize;
    user-select: none;
}

.workflow-panel,
.control-panel,
.content-column {
    min-width: 0;
}

.control-panel {
    grid-area: controls;
    position: sticky;
    top: 0;
    min-height: inherit;
    border-right: 0.1rem solid var(--ods-gray-300);
    background: var(--ods-white-100);
}

.panel-resizer {
    grid-area: resizer;
    align-self: stretch;
    width: 0.5rem;
    min-height: inherit;
    padding: 0;
    border: 0;
    border-left: 0.1rem solid var(--ods-gray-300);
    border-right: 0.1rem solid transparent;
    background: transparent;
    cursor: col-resize;
    transition: background-color 0.15s ease, border-color 0.15s ease;
}

.panel-resizer:hover,
.panel-resizer:focus-visible,
.top-layout.is-resizing .panel-resizer {
    border-left-color: var(--ods-orange-100);
    background: rgba(255, 121, 0, 0.1);
    outline: none;
}

.content-column {
    grid-area: workflow;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    min-height: inherit;
    padding: 1.5rem 1rem 2rem;
}

.workflow-panel {
    min-width: 0;
}

.workspace-steps {
    display: flex;
    align-items: center;
    gap: 1rem;
    min-height: 4rem;
    padding: 0.25rem 0 1rem;
    color: var(--ods-gray-700);
    font-weight: 700;
}

.step-item {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
}

.step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    border: 0.15rem solid var(--ods-gray-400);
    color: var(--ods-gray-700);
    background: var(--ods-white-100);
    font-size: 1rem;
}

.step-item.is-done,
.step-item.is-active {
    color: var(--ods-black-900);
}

.step-item.is-done .step-number,
.step-item.is-active .step-number {
    border-color: var(--ods-orange-100);
    background: var(--ods-orange-100);
    color: var(--ods-white-100);
}

.step-divider {
    color: var(--ods-gray-500);
}

.control-card {
    margin: 1.5rem;
    padding: 1.5rem;
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.5rem;
    background: var(--ods-white-100);
    box-shadow: 0 1rem 2.5rem rgba(0, 0, 0, 0.05);
}

.results-section,
.parsing-section {
    min-width: 0;
}

.parsing-card {
    --ods-orange-100: #ff7900;
    --ods-white-100: #fff;
    --ods-gray-300: #ddd;
    --ods-gray-700: #595959;
    --ods-black-900: #000;

    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.25rem 1.5rem;
    border: 0.1rem solid var(--ods-gray-300);
    border-left: 0.25rem solid var(--ods-orange-100);
    border-radius: 0.5rem;
    background: var(--ods-white-100);
    box-shadow: 0 1rem 2.5rem rgba(0, 0, 0, 0.05);
}

.parsing-spinner {
    flex-shrink: 0;
    width: 1.75rem;
    height: 1.75rem;
    border-width: 0.2rem;
    color: var(--ods-orange-100);
}

.parsing-body {
    min-width: 0;
}

.parsing-title {
    font-weight: 700;
    color: var(--ods-black-900);
}

.parsing-detail {
    font-size: 0.85rem;
    color: var(--ods-gray-700);
    word-break: break-word;
}

.results-card {
    padding: 1.5rem;
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.5rem;
    background: var(--ods-white-100);
    box-shadow: 0 1rem 2.5rem rgba(0, 0, 0, 0.05);
}

@media (max-width: 62rem) {
    .page-shell {
        min-height: auto;
    }

    .top-layout {
        grid-template-columns: 1fr;
        grid-template-areas:
            'controls'
            'workflow';
    }

    .control-panel {
        position: static;
        min-height: auto;
        border-right: none;
        border-bottom: 0.1rem solid var(--ods-gray-300);
    }

    .panel-resizer {
        display: none;
    }

    .content-column {
        min-height: auto;
        padding: 1rem;
    }

    .workspace-steps {
        flex-wrap: wrap;
        min-height: auto;
    }
}

@media (max-width: 36rem) {
    .page-intro {
        padding: 1.25rem 1rem 1rem;
    }

    .control-card {
        margin: 1rem;
        padding: 1rem;
    }

    .results-card {
        padding: 1rem;
    }
}

@media (min-width: 62rem) {
    .content-column {
        padding: 1.5rem 2rem 2rem;
    }
}

.validate-cta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    margin-top: 1.5rem;
    padding-top: 1.25rem;
    border-top: 0.1rem solid var(--ods-gray-300);
}

.validate-hint {
    font-size: 0.85rem;
    color: var(--ods-gray-700);
    margin: 0;
}

.btn-validate-cta {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.65rem 1.5rem;
    border-radius: 0.35rem;
    border: none;
    background: var(--ods-orange-100);
    color: var(--ods-white-100);
    font-size: 0.85rem;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
    transition: filter 0.15s, transform 0.15s;
}

.btn-validate-cta:hover {
    filter: brightness(0.85);
    transform: translateX(2px);
}
</style>
