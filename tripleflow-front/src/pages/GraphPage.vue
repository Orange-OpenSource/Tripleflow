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
    <main class="graph-shell">

        <!-- En-tête de page -->
        <div class="graph-intro">
            <div>
                <p class="eyebrow mb-2">Knowledge Graph</p>
                <h1 class="mb-2">Triple Graph</h1>
                <p class="page-subtitle mb-0">Visual exploration of extracted triples as a knowledge graph.</p>
            </div>
            <div class="graph-legend">
                <span class="legend-item"><span class="legend-dot is-validated"></span> Validated</span>
                <span class="legend-item"><span class="legend-dot is-rejected"></span> Rejected</span>
                <span class="legend-item"><span class="legend-dot is-review"></span> Needs review</span>
                <span class="legend-item"><span class="legend-dot is-pending"></span> Pending</span>
            </div>
        </div>

        <div class="graph-body">

            <!-- Barre latérale : filtres fichier + statut + infos nœud sélectionné -->
            <aside class="graph-sidebar">
                <p class="sidebar-title">Source files</p>
                <ul class="file-list list-unstyled mb-0">
                    <li :class="['file-item', { 'is-active': selectedFileId === null }]" @click="selectFile(null)">
                        <span class="file-name">All files</span>
                    </li>
                    <li
                        v-for="f in files" :key="f.file_id"
                        :class="['file-item', { 'is-active': selectedFileId === f.file_id }]"
                        @click="selectFile(f.file_id)"
                    >
                        <span class="file-name" :title="f.file_name">{{ f.file_name }}</span>
                    </li>
                    <li v-if="files.length === 0" class="file-item-empty">No files yet</li>
                </ul>

                <div class="sidebar-divider"></div>

                <p class="sidebar-title">Status filter</p>
                <div class="status-filters">
                    <button
                        v-for="s in statusFilters" :key="s.value"
                        :class="['filter-pill', { 'is-active': activeStatuses.includes(s.value) }]"
                        @click="toggleStatus(s.value)"
                    >
                        <span class="pill-dot" :style="{ background: STATUS_COLORS[s.value] }"></span>
                        {{ s.label }}
                        <span class="filter-count">{{ s.count }}</span>
                    </button>
                </div>

                <div class="sidebar-divider"></div>

                <div class="sidebar-actions">
                    <button class="btn btn-sm btn-outline-secondary w-100" @click="reheat">
                        <svg width="25" height="25" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false" class="btn-icon">
                            <path fill-rule="evenodd" d="M782.856,217.17a0.08,0.08,0,0,1-.013-0.013,400,400,0,0,0-565.686,0c-156.21,156.21-156.21,409.476,0,565.686a400,400,0,0,0,565.686,0L676.777,676.777a250,250,0,1,1,0-353.554l0.028,0.027L575.083,425H825a50,50,0,0,0,50-50h0V125Z" transform="scale(.96)" fill="currentColor"/>
                        </svg>
                        Re-layout
                    </button>
                    <button class="btn btn-sm btn-outline-secondary w-100 mt-2" @click="zoomFit">
                        <svg width="25" height="25" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false" class="btn-icon">
                            <g transform="scale(.96)"><path fill-rule="evenodd" d="M125,125V375h75V200H375V125H125Zm675,0H625v75H800V375h75V125H800Zm0,675H625v75H875V625H800V800ZM200,625H125V875H375V800H200V625Z" fill="currentColor"/></g>
                        </svg>
                        Fit view
                    </button>
                </div>

                <!-- Détail du nœud cliqué -->
                <template v-if="selectedNode">
                    <div class="sidebar-divider"></div>
                    <p class="sidebar-title">Selected entity</p>
                    <div class="node-detail">
                        <p class="node-label">{{ selectedNode.label }}</p>
                        <p class="node-stats">
                            <span>{{ selectedNode.outLinks }} outgoing</span>
                            <span>{{ selectedNode.inLinks }} incoming</span>
                        </p>
                        <button class="btn btn-sm btn-outline-secondary w-100 mt-2" @click="clearSelection">
                            Clear selection
                        </button>
                    </div>
                </template>
            </aside>

            <!-- Zone canvas force-graph -->
            <div class="graph-area">
                <div v-if="isLoading" class="graph-state">Loading triples...</div>
                <div v-else-if="error" class="alert alert-danger m-3">{{ error }}</div>
                <div v-else-if="triples.length === 0" class="graph-state">No triples found.</div>
                <!-- Le canvas force-graph est injecté ici par la lib -->
                <div ref="graphContainer" class="fg-container"></div>
            </div>
        </div>

    </main>
</template>


<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import ForceGraph from 'force-graph'
import { fetchFiles, fetchFileTriples, fetchTriples } from '../composables/validation/api.js'
import { isNullLikeEntityValue, ENTITY_PLACEHOLDER } from '../composables/entity.js'

// ── Palette Orange / statuts ─────────────────────────────────────────────────
const ORANGE     = '#ff7900'
const ORANGE_DIM = 'rgba(255,121,0,0.15)'
const STATUS_COLORS = {
    validated:    '#228722',
    rejected:     '#cd3c14',
    needs_review: '#fc0',
    pending:      '#999',
}

// ── Refs Vue ─────────────────────────────────────────────────────────────────
const graphContainer = ref(null)  // div cible du canvas
let fg = null                      // instance ForceGraph (hors réactivité Vue)

const triples       = ref([])
const files         = ref([])
const isLoading     = ref(false)
const error         = ref('')
const selectedFileId  = ref(null)
const selectedNode    = ref(null)
const activeStatuses  = ref(['pending', 'validated', 'rejected', 'needs_review'])

// Sets utilisés pour le highlighting — stockés en dehors de Vue (pas besoin de réactivité)
let highlightNodes = new Set()
let highlightLinks = new Set()

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Renvoie le label lisible d'une entité (objet avec .label ou string brut). */
function entityLabel(part) {
    const candidate = part?.label ?? part
    return isNullLikeEntityValue(candidate) ? ENTITY_PLACEHOLDER : String(candidate).trim()
}

// ── Filtres calculés ─────────────────────────────────────────────────────────

const statusFilters = computed(() => {
    const counts = { pending: 0, validated: 0, rejected: 0, needs_review: 0 }
    for (const t of triples.value) {
        const s = t.status ?? 'pending'
        counts[s] = (counts[s] || 0) + 1
    }
    return [
        { value: 'pending',      label: 'Pending',      count: counts.pending },
        { value: 'validated',    label: 'Validated',    count: counts.validated },
        { value: 'rejected',     label: 'Rejected',     count: counts.rejected },
        { value: 'needs_review', label: 'Needs review', count: counts.needs_review },
    ]
})

/** Triplets visibles selon les statuts cochés. */
const visibleTriples = computed(() =>
    triples.value.filter(t => activeStatuses.value.includes(t.status ?? 'pending'))
)

// ── Chargement données ────────────────────────────────────────────────────────

async function load() {
    isLoading.value = true
    error.value = ''
    try {
        triples.value = selectedFileId.value
            ? await fetchFileTriples(selectedFileId.value)
            : await fetchTriples()
    } catch (e) {
        error.value = e.message
    } finally {
        isLoading.value = false
    }
}

async function loadFiles() {
    try { files.value = await fetchFiles() } catch { /* non-bloquant */ }
}

function selectFile(id) {
    selectedFileId.value = id
    load()
}

function toggleStatus(s) {
    const idx = activeStatuses.value.indexOf(s)
    // On garde toujours au moins un statut actif
    if (idx === -1) activeStatuses.value.push(s)
    else if (activeStatuses.value.length > 1) activeStatuses.value.splice(idx, 1)
}

// ── Construction du graphe ────────────────────────────────────────────────────

/**
 * Convertit la liste de triplets en { nodes, links } pour force-graph.
 *
 * Pourquoi des IDs numériques ("n0", "n1") ?
 * force-graph résout les source/target des liens par comparaison d'ID.
 * Si on utilisait le label brut comme ID, les espaces et caractères spéciaux
 * (slash, deux-points, parenthèses...) peuvent casser la résolution.
 */
function buildGraphData(tlist) {
    const labelToId = new Map()
    const nodes = []
    const links = []
    let counter = 0

    function getNodeId(label) {
        if (!labelToId.has(label)) {
            const id = `n${counter++}`
            labelToId.set(label, id)
            nodes.push({ id, label })
        }
        return labelToId.get(label)
    }

    for (const t of tlist) {
        const srcId  = getNodeId(entityLabel(t.subject))
        const tgtId  = getNodeId(entityLabel(t.obj))
        const status = t.status ?? 'pending'

        links.push({
            id:     t.triple_id,
            source: srcId,
            target: tgtId,
            label:  entityLabel(t.predicate),
            status,
        })
    }

    return { nodes, links }
}

// ── Initialisation force-graph ────────────────────────────────────────────────

/**
 * Crée (ou recrée) l'instance ForceGraph dans le div conteneur.
 *
 * force-graph fonctionne avec des CALLBACKS de rendu :
 *  - nodeColor    → appelé à chaque frame pour colorier chaque nœud
 *  - linkColor    → idem pour chaque arête
 *  - nodeCanvasObject → dessine le nœud sur le canvas (cercle + label)
 *
 * Le highlighting utilise deux Sets (highlightNodes, highlightLinks).
 * Quand un nœud est cliqué, on remplit ces Sets puis on appelle fg.refresh()
 * pour forcer un nouveau rendu.
 */
function initGraph(data) {
    if (!graphContainer.value) return

    // Nettoyage de l'instance précédente si elle existe
    if (fg) {
        fg._destructor?.()
        graphContainer.value.innerHTML = ''
        fg = null
    }

    highlightNodes.clear()
    highlightLinks.clear()
    selectedNode.value = null

    const { width, height } = graphContainer.value.getBoundingClientRect()

    fg = ForceGraph()(graphContainer.value)
        .width(width || 800)
        .height(height || 600)
        .graphData(data)

        // ── Nœuds ──
        // nodeCanvasObjectMode 'replace' : on gère entièrement le dessin du nœud
        .nodeCanvasObjectMode(() => 'replace')
        .nodeCanvasObject((node, ctx, globalScale) => {
            const isHL = !highlightNodes.size || highlightNodes.has(node)

            // Cercle du nœud
            const r = 5
            ctx.beginPath()
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
            ctx.fillStyle = isHL ? ORANGE : ORANGE_DIM
            ctx.fill()
            if (isHL) {
                ctx.strokeStyle = '#ff7900'
                ctx.lineWidth = 1.5
                ctx.stroke()
            }

            // Label — affiché uniquement si le zoom est suffisant (évite la bouillie)
            if (globalScale >= 0.6) {
                const fontSize = Math.min(15, 10 / globalScale)
                ctx.font = `${fontSize}px HelvNeueOrange, Helvetica Neue, Arial, sans-serif`
                ctx.textAlign = 'center'
                ctx.textBaseline = 'top'

                const maxLen = 20
                const txt = node.label.length > maxLen
                    ? node.label.slice(0, maxLen - 1) + '…'
                    : node.label

                ctx.fillStyle = isHL ? '#333' : '#999'
                ctx.fillText(txt, Math.round(node.x), Math.round(node.y + r + 5))
            }
        })
        // Zone cliquable du nœud (doit correspondre au cercle dessiné)
        .nodePointerAreaPaint((node, color, ctx) => {
            ctx.fillStyle = color
            ctx.beginPath()
            ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI)
            ctx.fill()
        })

        // ── Arêtes ──
        .linkColor(link => {
            if (!highlightLinks.size) return STATUS_COLORS[link.status] ?? STATUS_COLORS.pending
            return highlightLinks.has(link)
                ? STATUS_COLORS[link.status] ?? STATUS_COLORS.pending
                : 'rgba(153,153,153,0.1)'
        })
        .linkWidth(link => highlightLinks.has(link) ? 2.5 : 1)
        .linkDirectionalArrowLength(5)           // flèche pour montrer la direction
        .linkDirectionalArrowRelPos(1)            // flèche au bout de l'arête
        .linkLabel(link => `${link.label} (${link.status})`)  // tooltip au survol

        // ── Interactions ──
        .onNodeClick(handleNodeClick)
        .onBackgroundClick(clearSelection)
        .backgroundColor('#eee')
}

// ── Highlighting ──────────────────────────────────────────────────────────────

/**
 * Au clic sur un nœud :
 * 1. On remplit highlightNodes avec le nœud cliqué + ses voisins directs
 * 2. On remplit highlightLinks avec les arêtes connectées
 *
 * Important : après init, force-graph remplace les string IDs des links
 * par les références d'objets nœuds. On compare donc par référence (===).
 */
function handleNodeClick(node) {
    highlightNodes.clear()
    highlightLinks.clear()

    if (node) {
        highlightNodes.add(node)
        fg.graphData().links.forEach(link => {
            if (link.source === node || link.target === node) {
                highlightLinks.add(link)
                highlightNodes.add(link.source)
                highlightNodes.add(link.target)
            }
        })

        const outLinks = fg.graphData().links.filter(l => l.source === node).length
        const inLinks  = fg.graphData().links.filter(l => l.target === node).length
        selectedNode.value = { label: node.label, outLinks, inLinks }
    }

    fg.refresh()  // force un nouveau rendu canvas
}

function clearSelection() {
    highlightNodes.clear()
    highlightLinks.clear()
    selectedNode.value = null
    fg?.refresh()
}

/** Relance la simulation physique (les nœuds se replacent). */
function reheat() {
    fg?.d3ReheatSimulation()
}

/** Zoom pour tout voir. */
function zoomFit() {
    fg?.zoomToFit(400, 40)
}

// ── Réactivité : on reconstruit le graphe quand les triplets visibles changent ─

watch(visibleTriples, async () => {
    await nextTick()
    initGraph(buildGraphData(visibleTriples.value))
}, { deep: false })

// ── Cycle de vie ──────────────────────────────────────────────────────────────

onMounted(async () => {
    await Promise.all([load(), loadFiles()])
})

onBeforeUnmount(() => {
    fg?._destructor?.()
    fg = null
})
</script>


<style scoped>
:root, * {
    --ods-orange-100: #ff7900;
}

/* ── Shell ── */
.graph-shell {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #eee;
    overflow: hidden;
}

/* ── En-tête ── */
.graph-intro {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.25rem;
    padding: 2rem 2rem 1.25rem;
    background: #fff;
    border-bottom: 2px solid var(--ods-orange-100);
    flex-shrink: 0;
    flex-wrap: wrap;               /* wrap sur petits écrans */
}

.eyebrow {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ods-orange-100);
}

.graph-legend {
    display: flex;
    gap: 1.25rem;
    align-items: center;
    flex-wrap: wrap;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 0.875rem;
    color: #595959;
}

.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}
.legend-dot.is-validated { background: #228722; }
.legend-dot.is-rejected  { background: #cd3c14; }
.legend-dot.is-review    { background: #fc0; }
.legend-dot.is-pending   { background: #999; }

/* ── Layout body ── */
.graph-body {
    flex: 1;
    display: flex;
    overflow: hidden;
}

/* ── Sidebar ── */
.graph-sidebar {
    width: 220px;
    flex-shrink: 0;
    background: #fff;
    border-right: 1px solid #ddd;
    overflow-y: auto;
    padding: 1rem 0.75rem;
    display: flex;
    flex-direction: column;
}

.sidebar-title {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #999;
    margin-bottom: 0.5rem;
}

.file-list { margin: 0; }

.file-item {
    padding: 5px 10px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 0.875rem;
    color: #333;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: background 0.15s;
}
.file-item:hover     { background: #eee; }
.file-item.is-active { background: var(--ods-orange-100); color: #fff; font-weight: 600; }
.file-item-empty     { font-size: 0.8rem; color: #999; padding: 5px 10px; }

.sidebar-divider { border-top: 1px solid #eee; margin: 0.75rem 0; }

.status-filters { display: flex; flex-direction: column; gap: 5px; }

.filter-pill {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    border-radius: 20px;
    border: 1px solid #ddd;
    background: #eee;
    font-size: 0.8rem;
    font-family: inherit;          /* bouton hérite de la police Orange */
    cursor: pointer;
    transition: all 0.15s;
    color: #595959;
}
.filter-pill:hover     { border-color: var(--ods-orange-100); color: var(--ods-orange-100); }
.filter-pill.is-active { background: var(--ods-orange-100); color: #fff; border-color: var(--ods-orange-100); }
.filter-pill.is-active .filter-count { background: rgba(255,255,255,0.25); }

.pill-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

.filter-count {
    margin-left: auto;
    background: #ddd;
    border-radius: 10px;
    padding: 0 5px;
    font-size: 0.75rem;
    font-weight: 600;
}

.sidebar-actions { display: flex; flex-direction: column; }

.btn-icon {
    vertical-align: middle;
    margin-right: 5px;
    margin-bottom: 2px;
}

.node-detail {
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 0.75rem;
}
.node-label {
    font-weight: 600;
    font-size: 0.875rem;
    color: var(--ods-orange-100);
    margin-bottom: 0.25rem;
    word-break: break-word;
}
.node-stats {
    font-size: 0.75rem;
    color: #666;
    display: flex;
    gap: 10px;
    margin-bottom: 0;
}

/* ── Zone graphe ── */
.graph-area {
    flex: 1;
    position: relative;
    overflow: hidden;
}

.fg-container {
    width: 100%;
    height: 100%;
}

/* force-graph injecte un <canvas> direct dans fg-container */
.fg-container :deep(canvas) {
    display: block;
}

.graph-state {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #999;
    font-size: 1rem;
}

/* ── Responsive mobile ── */
@media (max-width: 768px) {
    .graph-intro {
        padding: 1.25rem 1rem 1rem;
        gap: 1rem;
    }

    .graph-body {
        flex-direction: column;
    }

    .graph-sidebar {
        width: 100%;
        height: auto;
        max-height: 200px;
        border-right: none;
        border-bottom: 1px solid #ddd;
        flex-direction: row;
        flex-wrap: wrap;
        overflow-x: auto;
        gap: 1rem;
        padding: 0.75rem 1rem;
    }

    .graph-sidebar .sidebar-title { display: none; }

    .file-list {
        display: flex;
        flex-direction: row;
        gap: 5px;
        flex-wrap: nowrap;
    }

    .status-filters { flex-direction: row; flex-wrap: wrap; }

    .sidebar-actions { flex-direction: row; gap: 5px; }
    .sidebar-actions .mt-2 { margin-top: 0 !important; }

    .graph-area {
        flex: 1;
        min-height: 400px;
    }
}

@media (max-width: 480px) {
    .graph-legend { gap: 0.75rem; }
    .legend-item  { font-size: 0.75rem; }
    .graph-sidebar { max-height: 150px; }
}
</style>
