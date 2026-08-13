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
    <section class="workflow-section">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h2 class="h4 mb-0">Workflow</h2>
            <span class="text-muted small">Visual pipeline of the extraction process</span>
        </div>

        <div v-if="isCompactLayout" class="workflow-mobile">
            <article class="compact-card workflow-node input-node active">
                <div class="node-header d-flex align-items-center gap-2 mb-3 fw-semibold text-dark">
                    <svg class="node-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M625,75V225c0,27.614,19.9,50,44.444,50H825Zm50,250a100,100,0,0,1-100-100V75H175V874.773h0.006c0,0.076-.006.151-0.006,0.227a50,50,0,0,0,50,50H825V325H675ZM325,375H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,375Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,475Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,575ZM425,725H325a25,25,0,0,1,0-50H425A25,25,0,0,1,425,725Z" transform="scale(.96)" fill="currentColor"/></svg>
                    <span>Input</span>
                </div>
                <div class="node-content text-center">
                    <span class="badge bg-light text-dark mb-2">{{ selectedExtractors.length > 0 ? selectedExtractors.join(' + ').toUpperCase() : 'NONE' }}</span>
                    <div class="status-text small text-muted">
                        {{ inputStatus === 'ready' ? 'Ready' : 'Waiting for input' }}
                    </div>
                </div>
            </article>

            <article
                v-if="parsingEnabled"
                class="compact-card workflow-node parse-node"
                :class="{ 'running': isParsing }"
            >
                <div class="node-header d-flex align-items-center gap-2 mb-3 fw-semibold text-dark">
                    <svg class="node-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M625,75V225c0,27.614,19.9,50,44.444,50H825Zm50,250a100,100,0,0,1-100-100V75H175V874.773h0.006c0,0.076-.006.151-0.006,0.227a50,50,0,0,0,50,50H825V325H675ZM325,375H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,375Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,475Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,575ZM425,725H325a25,25,0,0,1,0-50H425A25,25,0,0,1,425,725Z" transform="scale(.96)" fill="currentColor"/></svg>
                    <span>Parsing</span>
                    <div v-if="isParsing" class="spinner-border spinner-border-sm ms-2 parse-spinner" role="status"></div>
                </div>
                <div class="node-content text-center">
                    <div class="stage-name fw-bold mb-1">DOCLING</div>
                    <div class="status-text small text-muted">{{ parseStatusText }}</div>
                </div>
            </article>

            <article
                v-if="chunkingEnabled"
                class="compact-card workflow-node chunk-node"
                :class="{ 'running': isChunking }"
            >
                <div class="node-header d-flex align-items-center gap-2 mb-3 fw-semibold text-dark">
                    <svg class="node-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><g fill="currentColor"><rect x="120" y="120" width="300" height="300" rx="50"/><rect x="540" y="120" width="300" height="300" rx="50"/><rect x="120" y="540" width="300" height="300" rx="50"/><rect x="540" y="540" width="300" height="300" rx="50"/></g></svg>
                    <span>Chunking</span>
                </div>
                <div class="node-content text-center">
                    <div class="stage-name fw-bold mb-1">{{ chunkSize }} / {{ chunkOverlap }}</div>
                    <div class="status-text small text-muted">{{ chunkStatusText }}</div>
                </div>
            </article>

            <div
                v-for="extractor in selectedExtractors"
                :key="`compact-${extractor}`"
                class="compact-lane"
            >
                <div
                    class="compact-card workflow-node extract-node"
                    :class="getExtractNodeClass(extractor)"
                >
                    <div class="node-header d-flex align-items-center gap-2 mb-3 fw-semibold text-dark">
                        <svg class="node-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M827.568,500.5c0-110.61,120.715-26.921,64.516-162.6-56.231-135.681-82.391,8.823-160.606-69.384s66.333-104.365-69.36-160.562c-135.718-56.2-52.024,64.481-162.61,64.481-110.619,0-26.921-120.68-162.612-64.481s8.827,82.349-69.391,160.562S163.133,202.216,106.93,337.9C50.7,473.579,171.416,389.89,171.416,500.5S50.7,527.419,106.93,663.1c56.2,135.681,82.359-8.823,160.575,69.352,78.218,78.214-66.3,104.4,69.391,160.6s51.993-64.483,162.612-64.483c110.586,0,26.892,120.678,162.61,64.483,135.693-56.2-8.854-82.384,69.36-160.6,78.215-78.175,104.375,66.329,160.606-69.352C948.283,527.419,827.568,611.11,827.568,500.5ZM500,301.015c110.457,0,200,89.537,200,199.985S610.457,700.985,500,700.985,300,611.448,300,501,389.543,301.015,500,301.015Z" transform="scale(.96)" fill="currentColor"/></svg>
                        <span>Extraction</span>
                        <div v-if="getExtractStatus(extractor) === 'running'" class="spinner-border spinner-border-sm text-warning ms-2" role="status"></div>
                    </div>
                    <div class="node-content text-center">
                        <div class="extractor-name fw-bold text-primary mb-1">{{ extractor.toUpperCase() }}</div>
                        <div class="status-text small text-muted">{{ getExtractStatusText(extractor) }}</div>
                    </div>
                </div>

                <div class="compact-arrow" aria-hidden="true">
                    <svg class="arrow-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M413.96,118.76c0-25.84,21.4-46.8,47.88-46.8h29.2c26.48,0,47.92,20.96,47.92,46.8V676h176.4L511.12,875.36c-17.2,16.8-45.04,16.8-62.24,0L244.6,676h169.44V118.8h-0.08V118.76z" fill="currentColor"/></svg>
                </div>

                <div
                    class="compact-card workflow-node results-node"
                    :class="{
                        'done': getResultStatus(extractor) === 'done',
                        'error': getResultStatus(extractor) === 'error',
                        'clickable': canOpenResults(extractor)
                    }"
                    @dblclick="openResultsPanel(extractor)"
                >
                    <div class="node-header d-flex align-items-center gap-2 mb-3 fw-semibold text-dark">
                        <svg class="node-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><g transform="scale(.96) translate(188 250)"><polygon fill="currentColor" fill-rule="nonzero" points="541.666667 0 208.333333 333.333333 83.3333333 208.333333 0 291.666667 125 416.666667 208.333333 500 291.666667 416.666667 625 83.3333333"/></g></svg>
                        <span>Results</span>
                    </div>
                    <div class="node-content text-center">
                        <div class="results-count fw-bold text-success mb-1">
                            {{ getResultStatus(extractor) === 'done' ? `${getExtractorTriplesCount(extractor)} triples` : '--' }}
                        </div>
                        <div class="status-text small text-muted">
                            <span v-if="getResultStatus(extractor) === 'waiting'">Waiting...</span>
                            <span v-else-if="getResultStatus(extractor) === 'error'">Error</span>
                            <span v-else-if="getResultStatus(extractor) === 'done'">Ready</span>
                            <span v-else>Idle</span>
                        </div>
                        <div v-if="canOpenResults(extractor)" class="node-hint small mt-2">
                            Double-click to open
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div
            v-else
            ref="workflowCanvasRef"
            class="workflow-canvas"
            :class="{ 'is-panning': isPanning }"
            :style="canvasStyle"
            @mousedown="startPan"
        >
            <div class="workflow-world" :style="workflowWorldStyle">

                <div
                    class="workflow-node input-node"
                    :class="{ 'active': inputStatus === 'ready', 'dragging': isDragging === 'input' }"
                    :style="{ left: pixelsToRem(nodePositions.input.x), top: pixelsToRem(nodePositions.input.y) }"
                    @mousedown="startDrag('input', $event)"
                >
                    <div class="node-header d-flex align-items-center gap-2 mb-3 fw-semibold text-dark">
                        <svg class="node-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M625,75V225c0,27.614,19.9,50,44.444,50H825Zm50,250a100,100,0,0,1-100-100V75H175V874.773h0.006c0,0.076-.006.151-0.006,0.227a50,50,0,0,0,50,50H825V325H675ZM325,375H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,375Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,475Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,575ZM425,725H325a25,25,0,0,1,0-50H425A25,25,0,0,1,425,725Z" transform="scale(.96)" fill="currentColor"/></svg>
                        <span>Input</span>
                    </div>
                    <div class="node-content text-center">
                        <span class="badge bg-light text-dark mb-2">{{ selectedExtractors.length > 0 ? selectedExtractors.join(' + ').toUpperCase() : 'NONE' }}</span>
                        <div class="status-text small text-muted">
                            {{ inputStatus === 'ready' ? 'Ready' : 'Waiting for input' }}
                        </div>
                    </div>
                </div>

                <div
                    v-if="parsingEnabled"
                    class="workflow-node parse-node"
                    :class="{ 'dragging': isDragging === 'parse', 'running': isParsing }"
                    :style="{ left: pixelsToRem(getNodePosition('parse').x), top: pixelsToRem(getNodePosition('parse').y) }"
                    @mousedown="startDrag('parse', $event)"
                >
                    <div class="node-header d-flex align-items-center gap-2 mb-3 fw-semibold text-dark">
                        <svg class="node-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M625,75V225c0,27.614,19.9,50,44.444,50H825Zm50,250a100,100,0,0,1-100-100V75H175V874.773h0.006c0,0.076-.006.151-0.006,0.227a50,50,0,0,0,50,50H825V325H675ZM325,375H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,375Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,475Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,575ZM425,725H325a25,25,0,0,1,0-50H425A25,25,0,0,1,425,725Z" transform="scale(.96)" fill="currentColor"/></svg>
                        <span>Parsing</span>
                        <div v-if="isParsing" class="spinner-border spinner-border-sm ms-2 parse-spinner" role="status"></div>
                    </div>
                    <div class="node-content text-center">
                        <div class="stage-name fw-bold mb-1">DOCLING</div>
                        <div class="status-text small text-muted">{{ parseStatusText }}</div>
                    </div>
                </div>

                <div
                    v-if="chunkingEnabled"
                    class="workflow-node chunk-node"
                    :class="{ 'dragging': isDragging === 'chunk', 'running': isChunking }"
                    :style="{ left: pixelsToRem(getNodePosition('chunk').x), top: pixelsToRem(getNodePosition('chunk').y) }"
                    @mousedown="startDrag('chunk', $event)"
                >
                    <div class="node-header d-flex align-items-center gap-2 mb-3 fw-semibold text-dark">
                        <svg class="node-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><g fill="currentColor"><rect x="120" y="120" width="300" height="300" rx="50"/><rect x="540" y="120" width="300" height="300" rx="50"/><rect x="120" y="540" width="300" height="300" rx="50"/><rect x="540" y="540" width="300" height="300" rx="50"/></g></svg>
                        <span>Chunking</span>
                    </div>
                    <div class="node-content text-center">
                        <div class="stage-name fw-bold mb-1">{{ chunkSize }} / {{ chunkOverlap }}</div>
                        <div class="status-text small text-muted">{{ chunkStatusText }}</div>
                    </div>
                </div>

                <div
                    v-for="(extractor, index) in selectedExtractors"
                    :key="'extract-' + extractor"
                    class="workflow-node extract-node"
                    :class="{ ...getExtractNodeClass(extractor), 'dragging': isDragging === 'extract-' + extractor }"
                    :style="{ left: pixelsToRem(getNodePosition('extract', index).x), top: pixelsToRem(getNodePosition('extract', index).y) }"
                    @mousedown="startDrag('extract-' + extractor, $event)"
                >
                    <div class="node-header d-flex align-items-center gap-2 mb-3 fw-semibold text-dark">
                        <svg class="node-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M827.568,500.5c0-110.61,120.715-26.921,64.516-162.6-56.231-135.681-82.391,8.823-160.606-69.384s66.333-104.365-69.36-160.562c-135.718-56.2-52.024,64.481-162.61,64.481-110.619,0-26.921-120.68-162.612-64.481s8.827,82.349-69.391,160.562S163.133,202.216,106.93,337.9C50.7,473.579,171.416,389.89,171.416,500.5S50.7,527.419,106.93,663.1c56.2,135.681,82.359-8.823,160.575,69.352,78.218,78.214-66.3,104.4,69.391,160.6s51.993-64.483,162.612-64.483c110.586,0,26.892,120.678,162.61,64.483,135.693-56.2-8.854-82.384,69.36-160.6,78.215-78.175,104.375,66.329,160.606-69.352C948.283,527.419,827.568,611.11,827.568,500.5ZM500,301.015c110.457,0,200,89.537,200,199.985S610.457,700.985,500,700.985,300,611.448,300,501,389.543,301.015,500,301.015Z" transform="scale(.96)" fill="currentColor"/></svg>
                        <span>Extraction</span>
                        <div v-if="getExtractStatus(extractor) === 'running'" class="spinner-border spinner-border-sm text-warning ms-2" role="status"></div>
                    </div>
                    <div class="node-content text-center">
                        <div class="extractor-name fw-bold text-primary mb-1">{{ extractor.toUpperCase() }}</div>
                        <div class="status-text small text-muted">{{ getExtractStatusText(extractor) }}</div>
                    </div>
                </div>

                <div
                    v-for="(extractor, index) in selectedExtractors"
                    :key="'result-' + extractor"
                    class="workflow-node results-node"
                    :class="{
                        'done': getResultStatus(extractor) === 'done',
                        'error': getResultStatus(extractor) === 'error',
                        'dragging': isDragging === 'result-' + extractor,
                        'clickable': canOpenResults(extractor)
                    }"
                    :style="{ left: pixelsToRem(getNodePosition('result', index).x), top: pixelsToRem(getNodePosition('result', index).y) }"
                    @mousedown="startDrag('result-' + extractor, $event)"
                    @dblclick="openResultsPanel(extractor)"
                >
                    <div class="node-header d-flex align-items-center gap-2 mb-3 fw-semibold text-dark">
                        <svg class="node-icon" aria-hidden="true" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><g transform="scale(.96) translate(188 250)"><polygon fill="currentColor" fill-rule="nonzero" points="541.666667 0 208.333333 333.333333 83.3333333 208.333333 0 291.666667 125 416.666667 208.333333 500 291.666667 416.666667 625 83.3333333"/></g></svg>
                        <span>Results</span>
                    </div>
                    <div class="node-content text-center">
                        <div class="results-count fw-bold text-success mb-1">
                            {{ getResultStatus(extractor) === 'done' ? `${getExtractorTriplesCount(extractor)} triples` : '--' }}
                        </div>
                        <div class="status-text small text-muted">
                            <span v-if="getResultStatus(extractor) === 'waiting'">Waiting...</span>
                            <span v-else-if="getResultStatus(extractor) === 'error'">Error</span>
                            <span v-else-if="getResultStatus(extractor) === 'done'">Ready</span>
                            <span v-else>Idle</span>
                        </div>
                        <div v-if="canOpenResults(extractor)" class="node-hint small mt-2">
                            Double-click to open
                        </div>
                    </div>
                </div>

                <svg class="workflow-connections" width="100%" height="100%">
                    <template v-for="(stage, i) in preStages.slice(1)" :key="'chain-' + stage">
                        <line
                            :x1="getNodeAnchor(preStages[i], 0, 'right').x"
                            :y1="getNodeAnchor(preStages[i], 0, 'right').y"
                            :x2="getNodeAnchor(stage, 0, 'left').x"
                            :y2="getNodeAnchor(stage, 0, 'left').y"
                            :class="{ 'active': inputStatus === 'ready' }"
                            stroke-width="2"
                        />
                        <polygon
                            :points="getArrowPoints(getNodeAnchor(stage, 0, 'left'))"
                            :class="{ 'active': inputStatus === 'ready' }"
                        />
                    </template>

                    <template v-for="(extractor, index) in selectedExtractors" :key="'input-extract-' + extractor">
                        <line
                            :x1="getNodeAnchor(lastPreStage, 0, 'right').x"
                            :y1="getNodeAnchor(lastPreStage, 0, 'right').y"
                            :x2="getNodeAnchor('extract', index, 'left').x"
                            :y2="getNodeAnchor('extract', index, 'left').y"
                            :class="{ 'active': getExtractStatus(extractor) !== 'idle' || inputStatus === 'ready', 'animated': getExtractStatus(extractor) === 'running' }"
                            stroke-width="2"
                        />
                        <polygon
                            :points="getArrowPoints(getNodeAnchor('extract', index, 'left'))"
                            :class="{ 'active': getExtractStatus(extractor) !== 'idle' || inputStatus === 'ready', 'animated': getExtractStatus(extractor) === 'running' }"
                        />
                    </template>

                    <template v-for="(extractor, index) in selectedExtractors" :key="'extract-result-' + extractor">
                        <line
                            :x1="getNodeAnchor('extract', index, 'right').x"
                            :y1="getNodeAnchor('extract', index, 'right').y"
                            :x2="getNodeAnchor('result', index, 'left').x"
                            :y2="getNodeAnchor('result', index, 'left').y"
                            :class="{ 'active': getExtractStatus(extractor) === 'done' || getExtractStatus(extractor) === 'running' || getExtractStatus(extractor) === 'error', 'animated': getExtractStatus(extractor) === 'running' }"
                            stroke-width="2"
                        />
                        <polygon
                            :points="getArrowPoints(getNodeAnchor('result', index, 'left'))"
                            :class="{ 'active': getExtractStatus(extractor) === 'done' || getExtractStatus(extractor) === 'running' || getExtractStatus(extractor) === 'error', 'animated': getExtractStatus(extractor) === 'running' }"
                        />
                    </template>
                </svg>
            </div>
        </div>
    </section>
</template>

<script setup>
/**
 * Visual pipeline diagram showing the extraction workflow: Input → Extraction → Results.
 * Nodes are draggable and the canvas is pannable on desktop.
 * Switches to a compact vertical layout on screens narrower than 1200px.
 */
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useExtractionState } from '../../composables/UseExtractionState'

const {
    text,
    selectedExtractors,
    selectedFileName,
    extractorElapsedTimes,
    extractorFinalTimes,
    extractorErrors,
    triples,
    parsingEnabled,
    isParsing,
    parsingProgress,
    isLoading,
    chunkingEnabled,
    chunkSize,
    chunkOverlap,
    chunkCount,
} = useExtractionState()

// The chunking step lives inside the /extract call, so it has no progress of its
// own: the node simply shows it takes part in the run under way.
const isChunking = computed(() => chunkingEnabled.value && isLoading.value)

/** Label under the Chunking node: the chunk count once a run reported it, the params otherwise. */
const chunkStatusText = computed(() => {
    if (chunkCount.value === null) {
        return 'size / overlap'
    }

    return chunkCount.value > 1 ? `${chunkCount.value} chunks` : '1 chunk'
})

/** Label under the Parsing node: file progress while running, otherwise a reminder that the step is optional. */
const parseStatusText = computed(() => {
    if (!isParsing.value) {
        return 'Optional step'
    }

    const { current, total } = parsingProgress.value
    return total > 1 ? `Parsing ${current}/${total}...` : 'Parsing...'
})

const baseX = 24
const columnGap = 186

const nodePositions = ref({
    input: { x: baseX, y: 68 },
})

const nodeWidth = 148
const nodeCenterY = 38

/**
 * Ordered list of pre-extraction stages shown in the pipeline.
 * Always starts with 'input'; the optional 'parse' and 'chunk' bricks are
 * inserted when the user enables them in the extraction form.
 */
const preStages = computed(() => {
    const stages = ['input']
    if (parsingEnabled.value) {
        stages.push('parse')
    }
    if (chunkingEnabled.value) {
        stages.push('chunk')
    }
    return stages
})

/** The last pre-extraction stage; every extractor node is fed from it. */
const lastPreStage = computed(() => preStages.value[preStages.value.length - 1])

/** X position (px) of the Extraction column, shifted right for each enabled pre-stage. */
const extractColumnX = computed(() => baseX + preStages.value.length * columnGap)

/** Default position of a pre-stage node from its index in the pipeline. */
function getPreStageDefault(stageId) {
    const index = preStages.value.indexOf(stageId)
    return { x: baseX + Math.max(index, 0) * columnGap, y: 68 }
}

const isDragging = ref(null)
const dragOffset = ref({ x: 0, y: 0 })
const isPanning = ref(false)
const panOffset = ref({ x: 0, y: 0 })
const panStart = ref({ x: 0, y: 0, offsetX: 0, offsetY: 0 })
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1440)
const workflowCanvasRef = ref(null)
const compactBreakpoint = 1200

/** Converts a pixel value to a rem string (assumes 16px root font size). */
function pixelsToRem(value) {
    return `${value / 16}rem`
}

const isCompactLayout = computed(() => viewportWidth.value < compactBreakpoint)

const workflowWorldStyle = computed(() => {
    const totalColumns = preStages.value.length + 2
    const worldWidth = baseX + totalColumns * columnGap + 40
    return {
        minWidth: pixelsToRem(worldWidth),
        transform: `translate(${pixelsToRem(panOffset.value.x)}, ${pixelsToRem(panOffset.value.y)})`
    }
})

const canvasStyle = computed(() => {
    if (selectedExtractors.value.length <= 1) {
        return { minHeight: '11.5rem' }
    }

    return { minHeight: '15rem' }
})

const getNodePosition = (type, index) => {
    if (type === 'input' || type === 'parse' || type === 'chunk') {
        return nodePositions.value[type] || getPreStageDefault(type)
    }

    const nodeId = `${type}-${selectedExtractors.value[index]}`

    if (nodePositions.value[nodeId]) {
        return nodePositions.value[nodeId]
    }

    const columnX = type === 'extract' ? extractColumnX.value : extractColumnX.value + columnGap

    if (selectedExtractors.value.length === 1) {
        return { x: columnX, y: 68 }
    }

    const baseY = 68
    const spacing = 72
    const totalHeight = (selectedExtractors.value.length - 1) * spacing
    const startY = baseY - totalHeight / 2

    return {
        x: columnX,
        y: startY + (index * spacing)
    }
}

/**
 * Returns the pixel coordinates of the left or right connection point of a workflow node.
 * Used to draw the SVG lines between nodes.
 */
function getNodeAnchor(type, index, side) {
    const position = getNodePosition(type, index)

    const xOffset = side === 'right' ? nodeWidth : 0

    return {
        x: position.x + xOffset,
        y: position.y + nodeCenterY
    }
}

/** Returns an SVG polygon points string for a small arrow head pointing right at the given anchor. */
function getArrowPoints(anchor) {
    return `${anchor.x - 8},${anchor.y - 5} ${anchor.x - 8},${anchor.y + 5} ${anchor.x},${anchor.y}`
}

const getExtractorTriplesCount = (extractor) => {
    if (!triples.value || !triples.value[extractor]) {
        return 0
    }
    return Array.isArray(triples.value[extractor]) ? triples.value[extractor].length : 0
}

const inputStatus = computed(() => {
    if (selectedFileName.value || text.value.trim()) {
        return 'ready'
    }
    return 'empty'
})

/** Returns the current status of an extractor node: 'idle', 'running', 'done', or 'error'. */
function getExtractStatus(extractor) {
    if (extractorFinalTimes.value[extractor] !== null && extractorFinalTimes.value[extractor] !== undefined) {
        if (extractorErrors.value[extractor]) {
            return 'error'
        }
        return 'done'
    }

    if (Object.prototype.hasOwnProperty.call(extractorElapsedTimes.value, extractor)) {
        return 'running'
    }

    return 'idle'
}

/** Returns the CSS class map for an extraction node based on its current status. */
function getExtractNodeClass(extractor) {
    return {
        running: getExtractStatus(extractor) === 'running',
        error: getExtractStatus(extractor) === 'error',
        done: getExtractStatus(extractor) === 'done',
    }
}

/** Returns a short status text displayed inside the extraction node. */
function getExtractStatusText(extractor) {
    if (getExtractStatus(extractor) === 'running') {
        return `Processing... ${extractorElapsedTimes.value[extractor] || 0}s`
    }

    if (getExtractStatus(extractor) === 'error') {
        return extractorErrors.value[extractor]
    }

    if (getExtractStatus(extractor) === 'done') {
        return `Completed in ${extractorFinalTimes.value[extractor]}s`
    }

    return 'Ready to extract'
}

/** Returns the status of the results node: 'idle', 'waiting', 'done', or 'error'. */
function getResultStatus(extractor) {
    if (getExtractStatus(extractor) === 'running') {
        return 'waiting'
    }

    if (extractorErrors.value[extractor]) {
        return 'error'
    }

    if (getExtractorTriplesCount(extractor) > 0 || getExtractStatus(extractor) === 'done') {
        return 'done'
    }

    return 'idle'
}

/** Returns true if the results node can be double-clicked to scroll to its results panel. */
function canOpenResults(extractor) {
    return getResultStatus(extractor) === 'done' || getResultStatus(extractor) === 'error'
}

/** Scrolls the page to the results panel for the given extractor. */
function openResultsPanel(extractor) {
    if (!canOpenResults(extractor) || typeof document === 'undefined') {
        return
    }

    const target = document.getElementById(`results-panel-${extractor}`)
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const startDrag = (nodeId, event) => {
    event.stopPropagation()
    isDragging.value = nodeId
    const container = workflowCanvasRef.value
    if (container) {
        const nodeRect = event.target.closest('.workflow-node').getBoundingClientRect()
        dragOffset.value = {
            x: event.clientX - nodeRect.left,
            y: event.clientY - nodeRect.top
        }
    }
    event.currentTarget.style.cursor = 'grabbing'
}

/** Starts panning the workflow canvas when the user clicks on the background (not on a node). */
function startPan(event) {
    if (event.target.closest('.workflow-node')) {
        return
    }

    isPanning.value = true
    panStart.value = {
        x: event.clientX,
        y: event.clientY,
        offsetX: panOffset.value.x,
        offsetY: panOffset.value.y
    }
}

const onMouseMove = (event) => {
    if (isPanning.value) {
        panOffset.value = {
            x: panStart.value.offsetX + event.clientX - panStart.value.x,
            y: panStart.value.offsetY + event.clientY - panStart.value.y
        }
        return
    }

    if (isDragging.value) {
        const container = workflowCanvasRef.value
        if (container) {
            const rect = container.getBoundingClientRect()
            const newX = event.clientX - rect.left - panOffset.value.x - dragOffset.value.x
            const newY = event.clientY - rect.top - panOffset.value.y - dragOffset.value.y

            nodePositions.value[isDragging.value] = {
                x: newX,
                y: newY
            }
        }
    }
}

const stopDrag = () => {
    if (isDragging.value) {
        isDragging.value = null
    }

    if (isPanning.value) {
        isPanning.value = false
    }
}

/** Updates the tracked viewport width on window resize and re-clamps the panel width. */
function updateViewportWidth() {
    if (typeof window !== 'undefined') {
        viewportWidth.value = window.innerWidth
    }
}

onMounted(() => {
    if (typeof window === 'undefined') {
        return
    }

    updateViewportWidth()
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', stopDrag)
    window.addEventListener('resize', updateViewportWidth)
})

onBeforeUnmount(() => {
    if (typeof window === 'undefined') {
        return
    }

    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', stopDrag)
    window.removeEventListener('resize', updateViewportWidth)
})
</script>

<style scoped>
.workflow-section,
.workflow-canvas,
.compact-arrow,
.workflow-node,
.extractor-badge,
.node-hint,
.status-text,
.workflow-connections {
    --ods-orange-100: #ff7900;
    --ods-white-100: #fff;
    --ods-gray-200: #eee;
    --ods-gray-300: #ddd;
    --ods-gray-400: #ccc;
    --ods-gray-500: #999;
    --ods-gray-700: #595959;
    --ods-black-900: #000;
    --ods-green-200: #32c832;
    --ods-red-200: #cd3c14;
    --ods-purple-500: #6e4aa7;
    --ods-pink-600: #bc4d9a;
    --node-input: #1677c8;
    --node-parse: var(--ods-purple-500);
    --node-chunk: var(--ods-pink-600);
    --node-extract: #ff7900;
    --node-result: #21a366;
}

.workflow-section {
    padding: 0.75rem;
    border: 0.1rem solid var(--ods-gray-300);
    border-radius: 0.5rem;
    background: var(--ods-white-100);
    height: 100%;
}

.workflow-canvas {
    position: relative;
    width: 100%;
    min-height: 11.5rem;
    background: var(--ods-white-100);
    border-radius: 0.5rem;
    border: 0.1rem solid var(--ods-gray-300);
    cursor: grab;
    overflow: hidden;
    user-select: none;
}

.workflow-canvas.is-panning {
    cursor: grabbing;
}

.workflow-world {
    position: absolute;
    inset: 0;
    min-width: 39rem;
    min-height: 20rem;
    transform-origin: 0 0;
    will-change: transform;
}

.workflow-mobile {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.compact-lane {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
}

.compact-card {
    position: relative;
    min-width: 0;
    width: 100%;
    cursor: default;
}

.compact-arrow {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--ods-gray-500);
}

.node-icon {
    width: 1rem;
    height: 1rem;
    flex-shrink: 0;
}

.arrow-icon {
    width: 1.1rem;
    height: 1.1rem;
}

.workflow-node {
    --node-accent: var(--ods-gray-400);
    --node-shadow: rgba(18, 28, 45, 0.08);
    position: absolute;
    z-index: 2;
    min-width: 9.5rem;
    padding: 0.65rem 0.85rem;
    border-radius: 0.9rem;
    background: var(--ods-white-100);
    border: 0.12rem solid var(--node-accent);
    transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
    box-shadow: 0 0.5rem 1.2rem var(--node-shadow);
    cursor: grab;
    user-select: none;
    overflow: hidden;
}

/*
 * Canvas nodes must be exactly nodeWidth (148px) wide: the SVG connection
 * anchors are computed from that constant, so any extra width would let the
 * node overlap and hide the start of its outgoing arrow.
 * Scoped to .workflow-world so the full-width compact cards keep their layout.
 */
.workflow-world .workflow-node {
    width: 9.25rem;
    min-width: 9.25rem;
}

.workflow-node.clickable {
    cursor: pointer;
}

.workflow-node.dragging {
    cursor: grabbing;
    z-index: 1000;
    box-shadow: 0 0.85rem 1.8rem rgba(18, 28, 45, 0.16);
    transform: scale(1.03);
}

.workflow-node:hover {
    box-shadow: 0 0.8rem 1.6rem color-mix(in srgb, var(--node-accent) 14%, rgba(18, 28, 45, 0.12));
}

.workflow-node.active {
    border-color: var(--node-accent);
}

.workflow-node.running {
    border-color: var(--node-accent);
    box-shadow: 0 0 0 0.18rem color-mix(in srgb, var(--node-accent) 12%, transparent), 0 0.75rem 1.5rem color-mix(in srgb, var(--node-accent) 12%, rgba(18, 28, 45, 0.12));
    animation: pulse 2s infinite;
}

.workflow-node.done {
    border-color: var(--node-accent);
}

.workflow-node.error {
    border-color: var(--ods-red-200);
    box-shadow: 0 0 0 0.18rem rgba(205, 60, 20, 0.1), 0 0.65rem 1.4rem rgba(205, 60, 20, 0.08);
}

.input-node {
    --node-accent: var(--node-input);
}

.parse-node {
    --node-accent: var(--node-parse);
}

.chunk-node {
    --node-accent: var(--node-chunk);
}

.parse-node .node-header,
.chunk-node .node-header {
    color: var(--node-accent) !important;
}

.parse-spinner {
    color: var(--node-accent);
}

.parse-node .stage-name,
.chunk-node .stage-name {
    color: var(--node-accent);
    font-size: 0.84rem;
    letter-spacing: 0.01em;
}

.extract-node {
    --node-accent: var(--node-extract);
}

.results-node {
    --node-accent: var(--node-result);
}

.node-header {
    padding-bottom: 0.55rem;
    border-bottom: 0.06rem solid color-mix(in srgb, var(--node-accent) 18%, white);
    margin-bottom: 0.55rem;
    font-size: 0.78rem;
    letter-spacing: 0.01em;
}

.node-content {
    text-align: center;
}

.input-node .node-header i,
.input-node .badge {
    color: var(--node-input) !important;
}

.extract-node .node-header i,
.extract-node .extractor-name {
    color: var(--node-extract) !important;
}

.results-node .node-header i,
.results-node .results-count {
    color: var(--node-result) !important;
}

.input-node .badge,
.compact-card.input-node .badge {
    background: color-mix(in srgb, var(--node-input) 10%, white) !important;
    border: 0.06rem solid color-mix(in srgb, var(--node-input) 20%, white);
    max-width: 100%;
    white-space: normal;
    word-break: break-word;
}

.extractor-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    background: var(--ods-gray-200);
    border-radius: 1rem;
    font-size: 1rem;
    font-weight: 500;
    color: var(--ods-gray-700);
    margin-bottom: 0.5rem;
}

.extractor-name {
    font-size: 0.84rem;
    margin-bottom: 0.2rem;
}

.results-count {
    font-size: 1.02rem;
    margin-bottom: 0.2rem;
    letter-spacing: -0.01em;
}

.node-hint {
    color: var(--ods-gray-700);
}

.status-text {
    font-size: 0.73rem;
    color: var(--ods-gray-700);
    line-height: 1.35;
}

.workflow-connections {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;
    z-index: 1;
}

.workflow-connections line {
    stroke: var(--ods-gray-300);
    stroke-dasharray: 5,5;
    transition: all 0.3s ease;
}

.workflow-connections line.active {
    stroke: var(--ods-black-900);
    stroke-dasharray: none;
}

.workflow-connections line.animated {
    stroke: var(--ods-orange-100);
}

.workflow-connections polygon {
    fill: var(--ods-gray-300);
    transition: all 0.3s ease;
}

.workflow-connections polygon.active {
    fill: var(--ods-black-900);
}

.workflow-connections polygon.animated {
    fill: var(--ods-orange-100);
    animation: dash 1s infinite;
}

@keyframes dash {
    to {
        stroke-dashoffset: -10;
    }
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}

@media (max-width: 48rem) {
    .workflow-canvas {
        min-height: 20rem;
    }
}

@media (max-width: 75rem) {
    .workflow-section {
        padding: 1rem;
    }

    .workflow-node {
        min-width: 0;
    }

    .workflow-node.clickable {
        cursor: pointer;
    }
}
</style>
