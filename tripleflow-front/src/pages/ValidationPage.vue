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
    <main class="val-shell">
        <div class="page-intro">
            <div>
                <p class="eyebrow mb-2">Triple Review</p>
                <h1 class="mb-2">Validate Triples</h1>
                <p class="page-subtitle mb-0">Review and validate extracted triples from MongoDB.</p>
            </div>
            <div class="reviewer-panel">
                <label class="reviewer-label" for="reviewer-name">
                    Reviewer <span class="required-star">*</span>
                </label>
                <input
                    id="reviewer-name"
                    v-model="reviewerName"
                    type="text"
                    :class="['reviewer-input', { 'is-required': reviewerNameMissing }]"
                    placeholder="Your name..."
                    @input="reviewerNameMissing = false"
                />
                <span v-if="reviewerNameMissing" class="reviewer-error">
                    Required before any action
                </span>
            </div>
        </div>

        <div class="val-toolbar">
            <div class="filter-pills" role="group" aria-label="Filter by status">
                <button
                    v-for="f in filters"
                    :key="f.value"
                    @click="activeFilter = f.value"
                    :class="['filter-pill', { 'is-active': activeFilter === f.value }]"
                >
                    {{ f.label }}
                    <span class="filter-count">{{ f.count }}</span>
                </button>
            </div>

            <div v-if="extractorGroups.length > 0" class="extractor-filters" role="group" aria-label="Filter by extractor">
                <span class="extractor-filter-label">Extractor</span>
                <button
                    :class="['filter-pill', { 'is-active': selectedExtractor === null }]"
                    @click="selectedExtractor = null"
                >All</button>
                <button
                    v-for="e in extractorGroups"
                    :key="e.name"
                    :class="['filter-pill is-extractor', { 'is-active': selectedExtractor === e.name }]"
                    @click="selectedExtractor = e.name"
                >
                    <span class="extractor-dot" :style="{ background: e.color }"></span>
                    {{ e.name }}
                    <span class="filter-count">{{ e.count }}</span>
                </button>
            </div>

            <div class="toolbar-right">
                <div class="export-group">
                    <span class="export-label">Export</span>
                    <button @click="exportJSON" :disabled="visibleTriples.length === 0" class="btn btn-sm btn-outline-secondary" title="Download filtered triples as JSON">
                        ↓ JSON
                    </button>
                    <button @click="exportTTL" :disabled="visibleTriples.length === 0" class="btn btn-sm btn-outline-secondary" title="Download filtered triples as Turtle/RDF">
                        ↓ TTL
                    </button>
                </div>
                <button @click="() => Promise.all([load(), loadFiles()])" :disabled="isLoading" class="btn btn-sm btn-outline-secondary">
                    ↺ Refresh
                </button>
            </div>
        </div>

        <div class="val-body">
            <aside class="file-sidebar">
                <p class="sidebar-title">Source files</p>
                <ul class="file-list list-unstyled mb-0">
                    <li
                        :class="['file-item', { 'is-active': selectedFileId === null }]"
                        @click="selectFile(null)"
                    >
                        <span class="file-name">All files</span>
                    </li>
                    <li
                        v-for="f in files"
                        :key="f.file_id"
                        :class="['file-item', { 'is-active': selectedFileId === f.file_id }]"
                        @click="selectFile(f.file_id)"
                    >
                        <div class="file-info">
                            <div class="file-name-row">
                                <input
                                    v-if="renamingFileId === f.file_id"
                                    v-focus
                                    type="text"
                                    class="file-rename-input"
                                    :value="getDisplayName(f)"
                                    @blur="confirmRename(f, $event.target.value)"
                                    @keydown.enter="$event.target.blur()"
                                    @keydown.escape="renamingFileId = null"
                                    @click.stop
                                />
                                <span
                                    v-else
                                    class="file-name"
                                    :title="getDisplayName(f)"
                                >{{ getDisplayName(f) }}</span>
                                <button
                                    v-if="renamingFileId !== f.file_id"
                                    class="file-rename-btn"
                                    :title="`Rename ${getDisplayName(f)}`"
                                    @click.stop="startRename(f)"
                                >
                                    <svg width="12" height="12" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path fill-rule="evenodd" d="M880,192L768,80a50,50,0,0,0-70.711,0L160,617.289V800H342.711L880,262.711A50,50,0,0,0,880,192ZM316,750H210V644l422-422,106,106Zm464-523L674,121l56-56,106,106Z" fill="currentColor"/></svg>
                                </button>
                            </div>
                            <span v-if="f.extraction_date" class="file-date">
                                {{ formatDate(f.extraction_date) }}
                            </span>
                        </div>
                        <span
                            v-if="f.review_progress?.pending > 0"
                            class="file-pending-badge"
                            :title="`${f.review_progress.pending} pending`"
                        >{{ f.review_progress.pending }}</span>
                    </li>
                    <li v-if="files.length === 0" class="file-item-empty">
                        No files yet
                    </li>
                </ul>

            </aside>

            <div class="table-section">
                <div v-if="isLoading" class="val-state">Loading triples...</div>
                <div v-else-if="error" class="alert alert-danger m-3" role="alert">{{ error }}</div>
                <div v-else-if="visibleTriples.length === 0" class="val-state">
                    No triples found for this filter.
                </div>

                <div v-else class="table-wrapper" :class="{ 'has-text-panel': sidePanelVisible }">
            <table class="triple-table">
                <thead>
                    <tr>
                        <th>Subject</th>
                        <th>Predicate</th>
                        <th>Object</th>
                        <th class="col-score">
                            <span class="score-th">
                                Score
                                <span class="score-info" tabindex="0" aria-label="Comment le score est calculé" aria-describedby="score-tooltip-text">
                                    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true" focusable="false">
                                        <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 1.5a8.5 8.5 0 1 1 0 17 8.5 8.5 0 0 1 0-17Zm-.9 6.6h1.8v6.4h-1.8v-6.4Zm.9-3.4a1.1 1.1 0 1 1 0 2.2 1.1 1.1 0 0 1 0-2.2Z"/>
                                    </svg>
                                    <span id="score-tooltip-text" class="score-tooltip" role="tooltip">
                                        <strong>Score de confiance</strong> du triplet, de 0 à 1 — plus il est élevé, plus l'extraction est jugée fiable.
                                        Score <strong>heuristique</strong> basé sur le nombre d'entités reliées à un QID (0&nbsp;→&nbsp;0.20, 1&nbsp;→&nbsp;0.45, 2&nbsp;→&nbsp;0.65, 3&nbsp;→&nbsp;0.85).
                                    </span>
                                </span>
                            </span>
                        </th>
                        <th class="col-actions">Actions</th>
                        <th class="col-status">Status</th>
                        <th class="col-extractor">Extractor</th>
                        <th class="col-review">Last review</th>
                    </tr>
                </thead>
                <tbody>
                    <template v-for="triple in visibleTriples" :key="triple.triple_id">
                        <tr :class="['triple-row', { 'is-pending-action': pendingAction?.id === triple.triple_id }]">
                            <td>
                                <a v-if="entityLink(triple.subject, 'item', triple)" :href="entityLink(triple.subject, 'item', triple)" target="_blank" rel="noopener noreferrer" class="entity-link">
                                    {{ entityLabel(triple.subject) }}
                                </a>
                                <span v-else>{{ entityLabel(triple.subject) }}</span>
                                <span v-if="entityId(triple.subject)" class="entity-id">{{ entityId(triple.subject) }}</span>
                            </td>
                            <td>
                                <a v-if="entityLink(triple.predicate, 'property', triple)" :href="entityLink(triple.predicate, 'property', triple)" target="_blank" rel="noopener noreferrer" class="entity-link is-predicate">
                                    {{ entityLabel(triple.predicate) }}
                                </a>
                                <span v-else class="is-predicate">{{ entityLabel(triple.predicate) }}</span>
                                <span v-if="entityId(triple.predicate)" class="entity-id">{{ entityId(triple.predicate) }}</span>
                            </td>
                            <td>
                                <a v-if="entityLink(triple.obj, 'item', triple)" :href="entityLink(triple.obj, 'item', triple)" target="_blank" rel="noopener noreferrer" class="entity-link">
                                    {{ entityLabel(triple.obj) }}
                                </a>
                                <span v-else>{{ entityLabel(triple.obj) }}</span>
                                <span v-if="entityId(triple.obj)" class="entity-id">{{ entityId(triple.obj) }}</span>
                            </td>

                            <td class="col-score">
                                <strong v-if="heuristicScore(triple) != null" class="score-value">{{ heuristicScore(triple).toFixed(2) }}</strong>
                                <span v-else class="score-none">—</span>
                            </td>

                            <td class="col-actions">
                                <div class="action-group">
                                    <button
                                        v-for="btn in actionButtons"
                                        :key="btn.status"
                                        @click="selectAction(triple.triple_id, btn.status)"
                                        :class="['action-btn', btn.cls, { 'is-selected': isPendingAction(triple.triple_id, btn.status) }]"
                                        :title="btn.label"
                                    >{{ btn.icon }}</button>
                                    <button
                                        v-if="triple.status === 'pending' || triple.status === 'needs_review'"
                                        type="button"
                                        :class="['action-btn', 'is-edit', { 'is-selected': pendingEdit?.id === triple.triple_id }]"
                                        title="Edit triple"
                                        @click="selectEdit(triple)"
                                    >✎</button>
                                </div>
                            </td>

                            <td class="col-status">
                                <Badge :badgeClass="statusClass(triple.status)">
                                    {{ triple.status?.replace('_', ' ') }}
                                </Badge>
                            </td>

                            <td class="col-extractor">
                                <div class="extractor-chips">
                                    <span
                                        v-for="ext in getExtractors(triple)"
                                        :key="ext"
                                        class="extractor-chip"
                                    >
                                        <span class="extractor-dot" :style="{ background: extractorColorMap[ext] || '#000' }"></span>
                                        {{ ext }}
                                    </span>
                                </div>
                            </td>

                            <td class="col-review">
                                <div v-if="lastReview(triple)" class="review-info">
                                    <span class="review-action">{{ lastReview(triple).action?.replace('_', ' ') }}</span>
                                    <span class="review-who">by {{ lastReview(triple).user_name || '?' }}</span>
                                    <span class="review-date">{{ formatDate(lastReview(triple).timestamp) }}</span>
                                    <span v-if="lastReview(triple).comments" class="review-comment" :title="lastReview(triple).comments">
                                        "{{ lastReview(triple).comments }}"
                                    </span>
                                </div>
                                <span v-else class="no-review">—</span>
                            </td>
                        </tr>

                        <tr v-if="pendingAction?.id === triple.triple_id" class="confirm-row">
                            <td colspan="7">
                                <div class="confirm-panel">
                                    <p class="confirm-label">
                                        Confirm <strong>{{ pendingAction.status.replace('_', ' ') }}</strong> for this triple?
                                    </p>
                                    <div class="confirm-body">
                                        <textarea
                                            v-model="pendingAction.comment"
                                            class="comment-input"
                                            placeholder="Comment (optional)..."
                                            rows="2"
                                        ></textarea>
                                        <div class="confirm-actions">
                                            <button @click="submitAction" class="btn btn-sm btn-primary" :disabled="isSubmitting">
                                                {{ isSubmitting ? 'Saving...' : 'Confirm' }}
                                            </button>
                                            <button @click="cancelAction" class="btn btn-sm btn-outline-secondary" :disabled="isSubmitting">
                                                Cancel
                                            </button>
                                            <span v-if="actionError" class="action-error">{{ actionError }}</span>
                                        </div>
                                    </div>
                                </div>
                            </td>
                        </tr>

                        <tr v-if="pendingEdit?.id === triple.triple_id" class="confirm-row">
                            <td colspan="7">
                                <div class="confirm-panel edit-panel">
                                    <p class="confirm-label">Edit triple</p>
                                    <div class="edit-fields">
                                        <div class="edit-field">
                                            <label class="edit-field-label">Subject</label>
                                            <EntitySearch v-model="pendingEdit.subject" type="item" :extractor="getExtractors(triple)[0]" />
                                        </div>
                                        <div class="edit-field">
                                            <label class="edit-field-label">Predicate</label>
                                            <EntitySearch v-model="pendingEdit.predicate" type="property" :extractor="getExtractors(triple)[0]" />
                                        </div>
                                        <div class="edit-field">
                                            <label class="edit-field-label">Object</label>
                                            <EntitySearch v-model="pendingEdit.obj" type="item" :extractor="getExtractors(triple)[0]" />
                                        </div>
                                    </div>
                                    <div class="confirm-body" style="margin-top: 0.75rem;">
                                        <div class="edit-footer">
                                            <select v-model="pendingEdit.status" class="edit-status-select">
                                                <option value="needs_review">Needs review</option>
                                                <option value="validated">Validated</option>
                                                <option value="rejected">Rejected</option>
                                            </select>
                                            <textarea
                                                v-model="pendingEdit.comment"
                                                class="comment-input"
                                                placeholder="Comment (optional)..."
                                                rows="2"
                                            ></textarea>
                                        </div>
                                        <div class="confirm-actions">
                                            <button @click="submitEdit" class="btn btn-sm btn-primary" :disabled="isSubmitting">
                                                {{ isSubmitting ? 'Saving...' : 'Save' }}
                                            </button>
                                            <button @click="cancelEdit" class="btn btn-sm btn-outline-secondary" :disabled="isSubmitting">
                                                Cancel
                                            </button>
                                            <span v-if="actionError" class="action-error">{{ actionError }}</span>
                                        </div>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>
                </div>
            </div>

            <aside v-if="sidePanelVisible && selectedFileId" class="text-panel" :style="{ width: panelWidth + 'px' }">
                <div class="text-panel-resizer" @mousedown="startResize"></div>
                <div class="text-panel-header">
                    <span class="text-panel-title">Source text</span>
                    <div class="text-panel-controls">
                        <div v-if="sideAnnotatedSegments" class="preview-legend">
                            <span class="legend-chip is-subject">Subject</span>
                            <span class="legend-chip is-predicate">Predicate</span>
                            <span class="legend-chip is-object">Object</span>
                        </div>
                        <button
                            v-if="sideAnnotatedSegments"
                            class="preview-toggle"
                            :class="{ 'is-active': sideHighlight }"
                            @click="sideHighlight = !sideHighlight"
                            title="Toggle highlighting"
                        >Highlight</button>
                        <button class="preview-close" @click="sidePanelVisible = false" title="Close" aria-label="Fermer le panneau">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" focusable="false">
                                <path d="M6 6l12 12M18 6L6 18"/>
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="text-panel-body">
                    <div v-if="sideLoading" class="val-state">Loading...</div>
                    <div v-else-if="sideError" class="preview-state preview-state-error">{{ sideError }}</div>
                    <div v-else class="preview-content">
                        <template v-if="sideHighlight && sideAnnotatedSegments">
                            <span
                                v-for="(seg, i) in sideAnnotatedSegments"
                                :key="i"
                                :class="seg.role ? `hl-${seg.role}` : null"
                            >{{ seg.text }}</span>
                        </template>
                        <template v-else>{{ sideContent }}</template>
                    </div>
                </div>
            </aside>
        </div>

        <section class="danger-zone" aria-label="Danger zone">
            <div class="danger-header">
                <h2 class="danger-title">Danger zone</h2>
                <p class="danger-subtitle">
                    Permanently clears all files and triples. Extractor configurations are kept.
                    Use once a review round is complete.
                </p>
            </div>

            <div v-if="!showResetConfirm" class="danger-actions">
                <button class="btn btn-sm btn-outline-secondary" @click="openFilesModal">
                    🗂 Manage files
                </button>
                <button class="btn btn-sm btn-danger-outline" @click="requestReset">
                    🗑 Clear database
                </button>
                <span v-if="reviewerNameMissing" class="danger-name-missing">
                    Le champ « Reviewer » (en haut) est manquant.
                </span>
                <span v-if="resetDoneMessage" class="reset-done">{{ resetDoneMessage }}</span>
            </div>

            <div v-else class="danger-confirm">
                <p class="danger-confirm-text">
                    This deletes <strong>all {{ files.length }} file(s)</strong> and
                    <strong>every triple</strong> for all users. This cannot be undone.
                </p>
                <label class="danger-confirm-label" for="reset-confirm-input">
                    Type <strong>RESET</strong> to confirm:
                </label>
                <input
                    id="reset-confirm-input"
                    v-model="resetConfirmText"
                    type="text"
                    class="danger-confirm-input"
                    placeholder="RESET"
                    autocomplete="off"
                    @keydown.enter="resetConfirmText.trim() === 'RESET' && resetDatabase()"
                />
                <div class="danger-confirm-actions">
                    <button
                        class="btn btn-sm btn-danger"
                        :disabled="isResetting || resetConfirmText.trim() !== 'RESET'"
                        @click="resetDatabase"
                    >
                        {{ isResetting ? 'Clearing…' : 'Yes, clear everything' }}
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" :disabled="isResetting" @click="cancelReset">
                        Cancel
                    </button>
                    <span v-if="resetError" class="action-error">{{ resetError }}</span>
                </div>
            </div>
        </section>

        <div v-if="showFilesModal" class="files-modal-overlay" @click.self="showFilesModal = false">
            <div class="files-modal" role="dialog" aria-modal="true" aria-label="Manage files">
                <div class="files-modal-header">
                    <h2 class="files-modal-title">Manage files</h2>
                    <button class="preview-close" @click="showFilesModal = false" aria-label="Close">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
                    </button>
                </div>

                <p v-if="!reviewerName.trim()" class="files-modal-warning">
                    Enter your reviewer name (top of the page) before deleting.
                </p>
                <span v-if="fileDeleteError" class="action-error">{{ fileDeleteError }}</span>

                <ul class="files-modal-list">
                    <li v-if="files.length === 0" class="files-modal-empty">No files.</li>
                    <li v-for="f in files" :key="f.file_id" class="files-modal-row">
                        <div class="files-modal-info">
                            <span class="files-modal-name" :title="getDisplayName(f)">{{ getDisplayName(f) }}</span>
                            <span class="files-modal-meta">
                                <template v-if="f.review_progress">
                                    {{ f.review_progress.pending }} pending · {{ f.review_progress.validated }} validated · {{ f.review_progress.rejected }} rejected
                                </template>
                                <template v-if="f.extraction_date"> · {{ formatDate(f.extraction_date) }}</template>
                            </span>
                        </div>

                        <div v-if="pendingFileDeleteId === f.file_id" class="files-modal-confirm">
                            <span>Delete this file and its triples?</span>
                            <button class="btn btn-sm btn-danger" :disabled="deletingFileId === f.file_id" @click="confirmFileDelete(f.file_id)">
                                {{ deletingFileId === f.file_id ? 'Deleting…' : 'Confirm' }}
                            </button>
                            <button class="btn btn-sm btn-outline-secondary" :disabled="deletingFileId === f.file_id" @click="pendingFileDeleteId = null">
                                Cancel
                            </button>
                        </div>
                        <button
                            v-else
                            class="btn btn-sm btn-danger-outline"
                            :disabled="!reviewerName.trim()"
                            @click="pendingFileDeleteId = f.file_id"
                        >🗑 Delete</button>
                    </li>
                </ul>
            </div>
        </div>
    </main>
</template>


<script setup>
/**
 * Triple validation page.
 * Lists extracted triples from MongoDB, with filters by status, extractor, and source file.
 * Allows a reviewer to approve, reject, flag for review, or inline-edit triples.
 */
import { computed, inject, nextTick, onMounted, onUnmounted, ref } from 'vue'
import Badge from '../components/atoms/Badge.vue'
import EntitySearch from '../components/molecules/EntitySearch.vue'
import { clearDatabase, deleteFile, fetchFiles, fetchFileContent, fetchFileTriples, fetchTriples, renameFile, submitValidation } from '../composables/validation/api.js'
import { isNullLikeEntityValue, ENTITY_PLACEHOLDER } from '../composables/entity.js'
import { buildEntityLink, WIKIDATA_BASE_URL } from '../composables/entityLinks.js'

const ALL_STATUSES = ['pending', 'validated', 'rejected', 'needs_review']

const LOCAL_NAMES_KEY = 'tripleflow-file-names'
const vFocus = { mounted: (el) => el.focus() }

const triples = ref([])
const files = ref([])
const renamingFileId = ref(null)
const localFileNames = ref(JSON.parse(localStorage.getItem(LOCAL_NAMES_KEY) || '{}'))
const isLoading = ref(false)
const error = ref('')
const activeFilter = ref('pending')
const selectedFileId = ref(null)
const selectedExtractor = ref(null)
const reviewerName = inject('reviewerName')
const pendingAction = ref(null)
const pendingEdit = ref(null)
const isSubmitting = ref(false)
const actionError = ref('')
const reviewerNameMissing = ref(false)

const showResetConfirm = ref(false)
const resetConfirmText = ref('')
const isResetting = ref(false)
const resetError = ref('')
const resetDoneMessage = ref('')

const showFilesModal = ref(false)
const pendingFileDeleteId = ref(null)
const deletingFileId = ref(null)
const fileDeleteError = ref('')

const sideContent = ref('')
const sideLoading = ref(false)
const sideError = ref('')
const sidePanelVisible = ref(false)
const sideHighlight = ref(true)
const panelWidth = ref(384)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartWidth = ref(0)

function startResize(e) {
    isDragging.value = true
    dragStartX.value = e.clientX
    dragStartWidth.value = panelWidth.value
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'col-resize'
    window.addEventListener('mousemove', onResize)
    window.addEventListener('mouseup', stopResize)
    e.preventDefault()
}

function onResize(e) {
    if (!isDragging.value) return
    const delta = dragStartX.value - e.clientX
    panelWidth.value = Math.min(Math.max(dragStartWidth.value + delta, 200), window.innerWidth * 0.6)
}

function stopResize() {
    isDragging.value = false
    document.body.style.userSelect = ''
    document.body.style.cursor = ''
    window.removeEventListener('mousemove', onResize)
    window.removeEventListener('mouseup', stopResize)
}

onUnmounted(() => {
    window.removeEventListener('mousemove', onResize)
    window.removeEventListener('mouseup', stopResize)
})

const actionButtons = [
    { status: 'validated', icon: '✓', label: 'Validate', cls: 'is-validate' },
    { status: 'needs_review', icon: '?', label: 'Needs review', cls: 'is-review' },
    { status: 'rejected', icon: '✗', label: 'Reject', cls: 'is-reject' },
]


/** Returns the display name for a file, using the local override if one exists. */
function getDisplayName(f) {
    return localFileNames.value[f.file_id] ?? f.file_name
}

/** Enters rename mode for a file. */
function startRename(f) {
    renamingFileId.value = f.file_id
}

/** Ensures the new name keeps the original file's extension if the user didn't include one. */
function withExtension(newName, originalName) {
    const extMatch = originalName.match(/\.[^.]+$/)
    if (!extMatch) return newName
    const ext = extMatch[0]
    return newName.endsWith(ext) ? newName : newName + ext
}

/** Saves the new name to MongoDB, updates localStorage as cache, and exits rename mode. */
async function confirmRename(f, newName) {
    const trimmed = withExtension(newName.trim(), f.file_name)
    renamingFileId.value = null

    if (!trimmed || trimmed === getDisplayName(f)) return

    localFileNames.value = { ...localFileNames.value, [f.file_id]: trimmed }
    localStorage.setItem(LOCAL_NAMES_KEY, JSON.stringify(localFileNames.value))

    try {
        await renameFile(f.file_id, trimmed)
        const target = files.value.find((file) => file.file_id === f.file_id)
        if (target) target.file_name = trimmed
    } catch {
        // keep the local override even if the backend call fails
    }
}

/** Returns the display label for a triple entity part (subject, predicate, or object). */
function entityLabel(part) {
    const candidate = part?.label ?? part
    return isNullLikeEntityValue(candidate) ? ENTITY_PLACEHOLDER : String(candidate).trim()
}

/** Returns the best available entity ID (id, qid, or pid) for a triple part. */
function entityId(part) {
    const candidate = part?.id ?? part?.qid ?? part?.pid ?? ''
    return isNullLikeEntityValue(candidate) ? '' : String(candidate).trim()
}

/**
 * Returns a link for a triple part, targeting the knowledge base declared by the extractor
 * that produced it, or an empty string when there is no declared alignment or the ID is not
 * a valid Q###/P### identifier.
 */
function entityLink(part, type, triple) {
    return buildEntityLink(entityId(part), type, getExtractors(triple)[0])
}

/**
 * Returns the heuristic score of a triple as a finite number, or null if absent.
 */
function heuristicScore(triple) {
    const raw = triple?.heuristic_score
    const value = typeof raw === 'string' ? Number(raw) : raw
    return typeof value === 'number' && Number.isFinite(value) ? value : null
}


/** Returns the Bootstrap badge class corresponding to a triple's validation status. */
function statusClass(status) {
    const map = {
        pending: 'text-bg-primary',
        validated: 'text-bg-success',
        rejected: 'text-bg-danger',
        needs_review: 'text-bg-warning',
    }
    return map[status] || 'text-bg-secondary'
}


/** Returns the most recent non-extraction history entry for a triple, or null if none exists. */
function lastReview(triple) {
    const human = (triple.history || []).filter(h => h.action !== 'extracted')
    return human[human.length - 1] || null
}

/** Formats an ISO timestamp into a localized French short date/time string. */
function formatDate(ts) {
    if (!ts) return ''
    const normalized = typeof ts === 'string' && !ts.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(ts)
        ? ts + 'Z'
        : ts
    return new Date(normalized).toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    })
}


/** Returns the list of extractor names that produced the given triple. */
function getExtractors(triple) {
    if (Array.isArray(triple.source?.extractors)) return triple.source.extractors
    if (triple.source?.extractor) return [triple.source.extractor]
    return []
}

const EXTRACTOR_COLORS = ['#085ebd', '#228722', '#ffcc00', '#492191', '#cd3c14']

const extractorGroups = computed(() => {
    const map = {}
    triples.value.forEach(t => {
        getExtractors(t).forEach(e => { map[e] = (map[e] || 0) + 1 })
    })
    return Object.entries(map).map(([name, count], i) => ({
        name,
        count,
        color: EXTRACTOR_COLORS[i % EXTRACTOR_COLORS.length],
    }))
})

const extractorColorMap = computed(() => {
    const map = {}
    extractorGroups.value.forEach(e => { map[e.name] = e.color })
    return map
})

const filteredByExtractor = computed(() => {
    if (!selectedExtractor.value) return triples.value
    return triples.value.filter(t => getExtractors(t).includes(selectedExtractor.value))
})

const countByStatus = computed(() => {
    const counts = Object.fromEntries(ALL_STATUSES.map(s => [s, 0]))
    filteredByExtractor.value.forEach(t => {
        if (counts[t.status] !== undefined) counts[t.status]++
    })
    return counts
})

const filters = computed(() => [
    { value: 'all', label: 'All', count: filteredByExtractor.value.length },
    ...ALL_STATUSES.map(s => ({
        value: s,
        label: s.replace('_', ' '),
        count: countByStatus.value[s],
    })),
])

const visibleTriples = computed(() => {
    if (activeFilter.value === 'all') return filteredByExtractor.value
    return filteredByExtractor.value.filter(t => t.status === activeFilter.value)
})


/** Returns true if the given triple/status combination is currently awaiting confirmation. */
function isPendingAction(id, status) {
    return pendingAction.value?.id === id && pendingAction.value?.status === status
}

/** Opens the confirmation panel for a validation action, or cancels it if already selected. Requires reviewer name. */
function selectAction(id, status) {
    if (!reviewerName.value.trim()) {
        reviewerNameMissing.value = true
        return
    }
    reviewerNameMissing.value = false
    if (isPendingAction(id, status)) {
        cancelAction()
        return
    }
    actionError.value = ''
    pendingEdit.value = null
    pendingAction.value = { id, status, comment: '' }
}

/** Dismisses the action confirmation panel without submitting. */
function cancelAction() {
    pendingAction.value = null
    actionError.value = ''
}

/** Opens the inline edit form for a triple, pre-filled with its current subject/predicate/object. Requires reviewer name. */
function selectEdit(triple) {
    if (!reviewerName.value.trim()) {
        reviewerNameMissing.value = true
        return
    }
    reviewerNameMissing.value = false
    if (pendingEdit.value?.id === triple.triple_id) {
        cancelEdit()
        return
    }
    pendingAction.value = null
    actionError.value = ''
    pendingEdit.value = {
        id: triple.triple_id,
        subject: { label: triple.subject?.label || '', id: triple.subject?.id || '' },
        predicate: { label: triple.predicate?.label || '', id: triple.predicate?.id || '' },
        obj: { label: triple.obj?.label || '', id: triple.obj?.id || '' },
        status: 'needs_review',
        comment: '',
    }
}

/** Closes the edit form without saving. */
function cancelEdit() {
    pendingEdit.value = null
    actionError.value = ''
}

/** Submits the edited triple to the API, then reloads the triple list and closes the form. */
async function submitEdit() {
    if (!pendingEdit.value) return
    isSubmitting.value = true
    actionError.value = ''
    try {
        const { subject, predicate, obj } = pendingEdit.value
        await submitValidation({
            triple_id: pendingEdit.value.id,
            status: pendingEdit.value.status,
            user_id: reviewerName.value,
            user_name: reviewerName.value,
            comment: pendingEdit.value.comment || null,
            modified_triple: {
                subject: { label: subject.label, id: subject.id || null },
                predicate: { label: predicate.label, id: predicate.id || null },
                obj: { label: obj.label, id: obj.id || null },
            },
        })
        await load()
        cancelEdit()
    } catch (e) {
        actionError.value = e.message
    } finally {
        isSubmitting.value = false
    }
}

/** Submits a validation action (approve/reject/flag) to the API, then reloads the triple list. */
async function submitAction() {
    if (!pendingAction.value) return
    isSubmitting.value = true
    actionError.value = ''
    try {
        await submitValidation({
            triple_id: pendingAction.value.id,
            status: pendingAction.value.status,
            user_id: reviewerName.value,
            user_name: reviewerName.value,
            comment: pendingAction.value.comment || null,
        })
        await load()
        cancelAction()
    } catch (e) {
        actionError.value = e.message
    } finally {
        isSubmitting.value = false
    }
}


/**
 * Splits text into annotated segments by matching triple labels (subject/predicate/object).
 * Returns null if no labels are long enough to match.
 */
function annotateText(text, triples) {
    const seen = new Set()
    const terms = []
    for (const t of triples) {
        for (const [part, role] of [
            [t.subject, 'subject'],
            [t.predicate, 'predicate'],
            [t.obj, 'object'],
        ]) {
            const label = part?.label?.trim()
            if (!label || label.length < 4) continue
            const key = label.toLowerCase()
            if (seen.has(key)) continue
            seen.add(key)
            terms.push({ label, role })
        }
    }
    if (terms.length === 0) return null
    terms.sort((a, b) => b.label.length - a.label.length)
    const pattern = terms
        .map(t => t.label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
        .join('|')
    const regex = new RegExp(`(${pattern})`, 'gi')
    return text.split(regex).map(chunk => ({
        text: chunk,
        role: terms.find(t => t.label.toLowerCase() === chunk.toLowerCase())?.role ?? null,
    }))
}

const sideAnnotatedSegments = computed(() => {
    if (!sideContent.value || triples.value.length === 0) return null
    return annotateText(sideContent.value, triples.value)
})

/** Switches the active file filter and reloads triples for the selected file (or all files if null). */
async function selectFile(fileId) {
    selectedFileId.value = fileId
    selectedExtractor.value = null
    await load()
    if (fileId) {
        sidePanelVisible.value = true
        sideLoading.value = true
        sideError.value = ''
        try {
            sideContent.value = await fetchFileContent(fileId)
        } catch (e) {
            sideError.value = e.message
        } finally {
            sideLoading.value = false
        }
    } else {
        sidePanelVisible.value = false
        sideContent.value = ''
    }
}

/** Fetches triples from the API for the currently selected file (or all files). */
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

/** Fetches the list of source files for the sidebar. Silently ignores errors. */
async function loadFiles() {
    try {
        files.value = await fetchFiles()
    } catch {
        files.value = []
    }
}

/** Wipes all files and triples from the backend, then refreshes the (now empty) view. */
async function resetDatabase() {
    if (!reviewerName.value.trim()) {
        reviewerNameMissing.value = true
        showResetConfirm.value = false
        return
    }
    if (resetConfirmText.value.trim() !== 'RESET') {
        return
    }
    isResetting.value = true
    resetError.value = ''
    resetDoneMessage.value = ''
    try {
        const result = await clearDatabase(reviewerName.value.trim())
        selectedFileId.value = null
        selectedExtractor.value = null
        sidePanelVisible.value = false
        showResetConfirm.value = false
        resetConfirmText.value = ''
        await Promise.all([load(), loadFiles()])
        resetDoneMessage.value = `Database cleared: ${result.files_deleted} file(s) and ${result.triples_deleted} triple(s) removed.`
    } catch (e) {
        resetError.value = e.message
    } finally {
        isResetting.value = false
    }
}

/** Shows the reset confirmation, but only once a reviewer name has been entered. */
function requestReset() {
    resetDoneMessage.value = ''
    if (!reviewerName.value.trim()) {
        reviewerNameMissing.value = true
        return
    }
    resetConfirmText.value = ''
    resetError.value = ''
    showResetConfirm.value = true
}

/** Closes the reset confirmation and clears its typed confirmation text. */
function cancelReset() {
    showResetConfirm.value = false
    resetConfirmText.value = ''
}

/** Opens the file-management modal (reviewer name required), clearing stale delete state. */
function openFilesModal() {
    if (!reviewerName.value.trim()) {
        reviewerNameMissing.value = true
        return
    }
    fileDeleteError.value = ''
    pendingFileDeleteId.value = null
    showFilesModal.value = true
}

/** Deletes a single file (and its triples) after confirmation, then refreshes the view. */
async function confirmFileDelete(fileId) {
    if (!reviewerName.value.trim()) {
        reviewerNameMissing.value = true
        showFilesModal.value = false
        return
    }
    deletingFileId.value = fileId
    fileDeleteError.value = ''
    try {
        await deleteFile(fileId, reviewerName.value.trim())
        if (selectedFileId.value === fileId) {
            selectedFileId.value = null
            sidePanelVisible.value = false
        }
        pendingFileDeleteId.value = null
        await Promise.all([load(), loadFiles()])
    } catch (e) {
        fileDeleteError.value = e.message
    } finally {
        deletingFileId.value = null
    }
}

onMounted(async () => {
    await Promise.all([load(), loadFiles()])
})


/** Builds a descriptive export filename that includes the active status and extractor/file filters. */
function buildExportFilename(ext) {
    const status = activeFilter.value === 'all' ? 'all' : activeFilter.value
    const extractor = selectedExtractor.value ? `_${selectedExtractor.value}` : ''
    const file = selectedFileId.value ? `_file${selectedFileId.value}` : ''
    return `triples_${status}${extractor}${file}.${ext}`
}

/** Triggers a browser download of the given content string as a named file. */
function downloadBlob(content, filename, mime) {
    const blob = new Blob([content], { type: mime })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
}

/** Exports the currently visible triples as a JSON file. */
function exportJSON() {
    const data = visibleTriples.value.map(t => ({
        triple_id: t.triple_id,
        subject: { label: entityLabel(t.subject), id: entityId(t.subject) || null },
        predicate: { label: entityLabel(t.predicate), id: entityId(t.predicate) || null },
        object: { label: entityLabel(t.obj), id: entityId(t.obj) || null },
        status: t.status,
        heuristic_score: heuristicScore(t),
        extractors: getExtractors(t),
        last_review: lastReview(t) ? {
            action: lastReview(t).action,
            user: lastReview(t).user_name,
            timestamp: lastReview(t).timestamp,
            comment: lastReview(t).comments || null,
        } : null,
    }))
    downloadBlob(JSON.stringify(data, null, 2), buildExportFilename('json'), 'application/json')
}

// Base URI used for wd:/wdt: prefixes in TTL exports. Instance-specific bases
// (e.g. an internal Wikibase) belong in the VITE_TTL_BASE_URL env var.
const TTL_BASE = import.meta.env.VITE_TTL_BASE_URL || WIKIDATA_BASE_URL

/**
 * Exports the currently visible triples as a Turtle/RDF file.
 * Uses wd:/wdt: prefixes for valid Wikidata-style IDs; falls back to commented-out lines for unresolved entities.
 */
function exportTTL() {
    const lines = [
        `@prefix wd: <${TTL_BASE}Item:> .`,
        `@prefix wdt: <${TTL_BASE}Property:> .`,
        `@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .`,
        `@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .`,
        '',
        `# Exported ${visibleTriples.value.length} triple(s) — status: ${activeFilter.value}`,
        `# Date: ${new Date().toISOString()}`,
        '',
    ]

    for (const t of visibleTriples.value) {
        const sId = entityId(t.subject)
        const pId = entityId(t.predicate)
        const oId = entityId(t.obj)
        const sLabel = entityLabel(t.subject)
        const pLabel = entityLabel(t.predicate)
        const oLabel = entityLabel(t.obj)

        const sUri = sId && /^Q\d+$/i.test(sId) ? `wd:${sId.toUpperCase()}` : null
        const pUri = pId && /^P\d+$/i.test(pId) ? `wdt:${pId.toUpperCase()}` : null
        const oUri = oId && /^Q\d+$/i.test(oId) ? `wd:${oId.toUpperCase()}` : null

        if (sUri && pUri && oUri) {
            lines.push(`${sUri} ${pUri} ${oUri} .`)
        } else {
            const s = sUri || `"${sLabel.replace(/"/g, '\\"')}"`
            const p = pUri || `"${pLabel.replace(/"/g, '\\"')}"`
            const o = oUri || `"${oLabel.replace(/"/g, '\\"')}"`
            lines.push(`# ${t.triple_id}: ${s} ${p} ${o}`)
        }
    }

    downloadBlob(lines.join('\n'), buildExportFilename('ttl'), 'text/turtle')
}
</script>


<style scoped>
.val-shell,
.page-intro,
.val-toolbar,
.triple-table,
.confirm-panel {
    --ods-orange-100: #ff7900;
    --ods-white-100: #fff;
    --ods-gray-200: #eee;
    --ods-gray-300: #ddd;
    --ods-gray-400: #ccc;
    --ods-gray-500: #999;
    --ods-gray-700: #595959;
    --ods-black-900: #000;
    --ods-green-dark: #228722;
    --ods-red-dark: #cd3c14;
    --ods-yellow: #ffcc00;
}

.val-shell {
    width: 100%;
    min-height: calc(100vh - 5rem);
    background: var(--ods-white-100);
}

.page-intro {
    display: flex;
    align-items: stretch;
    justify-content: space-between;
    border-bottom: 0.125rem solid var(--ods-gray-300);
    padding: 2rem 0 1.5rem 2rem;
    overflow: hidden;
}

.reviewer-panel {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 0.5rem;
    padding: 0 2rem;
    border-left: 0.125rem solid var(--ods-gray-300);
    flex-shrink: 0;
    min-width: 14rem;
    margin-left: 2rem;
}

.eyebrow {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.125em;
    color: var(--ods-gray-700);
    font-weight: 700;
}

.page-subtitle {
    color: var(--ods-gray-700);
    max-width: 44rem;
}

.val-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
    padding: 1rem 2rem;
    border-bottom: 0.125rem solid var(--ods-gray-200);
    background: var(--ods-white-100);
    position: sticky;
    top: 0;
    z-index: 10;
}

.filter-pills {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.filter-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.85rem;
    border-radius: 2rem;
    border: 0.125rem solid var(--ods-gray-300);
    background: var(--ods-white-100);
    color: var(--ods-gray-700);
    font-size: 0.875rem;
    font-weight: 400;
    cursor: pointer;
    text-transform: capitalize;
    transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.filter-pill:hover {
    border-color: var(--ods-orange-100);
    color: var(--ods-orange-100);
}

.filter-pill.is-active {
    background: var(--ods-orange-100);
    border-color: var(--ods-orange-100);
    color: var(--ods-white-100);
}

.filter-count {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1.25rem;
    height: 1.25rem;
    border-radius: 1rem;
    background: rgba(0, 0, 0, 0.15);
    font-size: 0.75rem;
    padding: 0 0.25rem;
}

.extractor-filters {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding-left: 1rem;
    border-left: 0.125rem solid var(--ods-gray-300);
}

.extractor-filter-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.125em;
    color: var(--ods-gray-500);
    font-weight: 700;
    white-space: nowrap;
}


.toolbar-right {
    display: flex;
    align-items: flex-end;
    gap: 1rem;
}

.export-group {
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

.export-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.125em;
    color: var(--ods-gray-500);
    font-weight: 700;
    white-space: nowrap;
    margin-right: 0.15rem;
}

.reviewer-label {
    display: block;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.125em;
    color: var(--ods-gray-500);
    font-weight: 700;
    margin-bottom: 0;
}

.reviewer-input {
    border: 0.125rem solid var(--ods-gray-300);
    border-radius: 0.25rem;
    padding: 0.375rem 0.65rem;
    font-size: 0.875rem;
    width: 100%;
    outline: none;
    font-family: inherit;
    background: var(--ods-white-100);
    color: var(--ods-black-900);
    transition: border-color 0.15s;
}

.reviewer-input:focus {
    border-color: var(--ods-orange-100);
    border-width: 0.15rem;
}

.reviewer-input.is-required {
    border-color: var(--ods-orange-100);
    border-width: 0.15rem;
}

.required-star {
    color: var(--ods-black-900);
}

.reviewer-error {
    display: block;
    font-size: 0.75rem;
    color: var(--ods-black-900);
    font-weight: 700;
}

.val-state {
    padding: 3rem 2rem;
    text-align: center;
    color: var(--ods-gray-500);
}

.val-body {
    display: flex;
    align-items: stretch;
    min-height: calc(100vh - 12rem);
}

.file-sidebar {
    width: 13rem;
    flex-shrink: 0;
    border-right: 0.125rem solid var(--ods-gray-300);
    padding: 1.25rem 0;
    background: var(--ods-white-100);
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: calc(100vh - 8rem);
    overflow-y: auto;
}

.sidebar-title {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.125em;
    color: var(--ods-gray-500);
    font-weight: 700;
    padding: 0 1rem 0.75rem;
    margin: 0;
    border-bottom: 0.125rem solid var(--ods-gray-200);
}

.file-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.65rem 1rem;
    cursor: pointer;
    font-size: 0.875rem;
    color: var(--ods-gray-700);
    border-left: 0.25rem solid transparent;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.file-item:hover {
    background: var(--ods-gray-200);
    color: var(--ods-black-900);
}

.file-item.is-active {
    border-left-color: var(--ods-orange-100);
    background: var(--ods-gray-200);
    color: var(--ods-black-900);
    font-weight: 700;
}

.file-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
}

.file-name-row {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    min-width: 0;
}

.file-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
    transition: color 0.15s;
}

.file-name:hover {
    color: var(--ods-orange-100);
    text-decoration: underline;
}

.file-rename-btn {
    flex-shrink: 0;
    display: none;
    border: none;
    background: transparent;
    padding: 0.15rem;
    cursor: pointer;
    color: var(--ods-gray-500);
    border-radius: 0.25rem;
    line-height: 1;
    transition: color 0.15s;
}

.file-item:hover .file-rename-btn {
    display: flex;
    align-items: center;
}

.file-rename-btn:hover {
    color: var(--ods-orange-100);
}

.file-rename-input {
    flex: 1;
    min-width: 0;
    border: none;
    border-bottom: 0.125rem solid var(--ods-orange-100);
    background: transparent;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0 0 0.125rem;
    outline: none;
    color: inherit;
}

.file-date {
    font-size: 0.75rem;
    color: var(--ods-gray-500);
}

.file-item.is-active .file-date {
    color: var(--ods-gray-700);
}

.file-pending-badge {
    flex-shrink: 0;
    min-width: 1.25rem;
    height: 1.25rem;
    border-radius: 1rem;
    background: var(--ods-orange-100);
    color: var(--ods-white-100);
    font-size: 0.75rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 0.25rem;
}

.file-item-empty {
    padding: 0.65rem 1rem;
    font-size: 0.75rem;
    color: var(--ods-gray-500);
    font-style: italic;
}

.table-section {
    flex: 1;
    min-width: 0;
}

.table-wrapper {
    padding: 1.5rem 2rem 2rem;
    overflow-x: auto;
    /* overflow-x: auto force overflow-y en auto : sans hauteur mini, le tooltip
       du score (qui s'ouvre vers le bas) est rogné quand il y a peu de lignes. */
    min-height: 18rem;
}

.triple-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
}

.triple-table thead th {
    padding: 0.65rem 0.85rem;
    text-align: left;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.125em;
    color: var(--ods-gray-700);
    border-bottom: 0.15rem solid var(--ods-gray-300);
    white-space: nowrap;
    background: var(--ods-white-100);
}

.triple-table tbody td {
    padding: 0.75rem 0.85rem;
    vertical-align: middle;
    border-bottom: 0.125rem solid var(--ods-gray-200);
    color: var(--ods-black-900);
}

.triple-row:hover td {
    background: var(--ods-gray-200);
}

.triple-row.is-pending-action td {
    background: var(--ods-gray-200);
}

.entity-link {
    color: var(--ods-black-900);
    text-decoration: none;
    font-weight: 400;
    border-bottom: 0.125rem solid var(--ods-gray-400);
    transition: border-color 0.15s, color 0.15s;
}

.entity-link:hover {
    color: var(--ods-orange-100);
    border-bottom-color: var(--ods-orange-100);
}

.entity-link.is-predicate,
span.is-predicate {
    color: var(--ods-gray-700);
    font-style: italic;
}

.entity-id {
    display: block;
    font-size: 0.75rem;
    color: var(--ods-gray-500);
    margin-top: 0.15rem;
}

.col-score {
    width: 5rem;
    text-align: center;
}

.score-value {
    color: var(--ods-green-dark);
    font-size: 0.75rem;
}

.score-none {
    color: var(--ods-gray-400);
}

.score-th {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
}

.score-info {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--ods-gray-500);
    cursor: help;
    line-height: 0;
}

.score-info:hover,
.score-info:focus-visible {
    color: var(--ods-orange-100);
    outline: none;
}

.score-tooltip {
    position: absolute;
    top: calc(100% + 0.5rem);
    left: 50%;
    transform: translateX(-50%);
    z-index: 20;
    width: 17.5rem;
    padding: 0.75rem 0.85rem;
    background: var(--ods-white-100);
    color: var(--ods-gray-700);
    border: 0.05rem solid var(--ods-gray-300);
    border-radius: 0.25rem;
    box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.15);
    font-size: 0.75rem;
    font-weight: 400;
    line-height: 1.5;
    text-transform: none;
    letter-spacing: normal;
    text-align: left;
    white-space: normal;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.15s ease;
    pointer-events: none;
}

.score-tooltip::before {
    content: '';
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 0.35rem solid transparent;
    border-bottom-color: var(--ods-gray-300);
}

.score-th:hover .score-tooltip,
.score-th:focus-within .score-tooltip {
    opacity: 1;
    visibility: visible;
}

.score-tooltip strong {
    color: var(--ods-black-900);
}

.score-tooltip ul {
    margin: 0.45rem 0 0;
    padding-left: 1rem;
}

.score-tooltip li {
    margin-bottom: 0.25rem;
}

.col-actions {
    width: 7rem;
    text-align: center;
}

.col-status {
    width: 7rem;
}

.col-extractor {
    width: 7rem;
}

.col-review {
    width: 13rem;
}

.action-group {
    display: flex;
    gap: 0.25rem;
    justify-content: center;
}

.action-btn {
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    border: 0.125rem solid var(--ods-gray-300);
    background: var(--ods-white-100);
    font-size: 0.875rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
    flex-shrink: 0;
}

.action-btn.is-validate:hover,
.action-btn.is-validate.is-selected {
    background: var(--ods-green-dark);
    border-color: var(--ods-green-dark);
    color: var(--ods-white-100);
}

.action-btn.is-review:hover,
.action-btn.is-review.is-selected {
    background: var(--ods-yellow);
    border-color: var(--ods-yellow);
    color: var(--ods-black-900);
}

.action-btn.is-reject:hover,
.action-btn.is-reject.is-selected {
    background: var(--ods-red-dark);
    border-color: var(--ods-red-dark);
    color: var(--ods-white-100);
}

.review-info {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    font-size: 0.75rem;
}

.review-action {
    font-weight: 700;
    text-transform: capitalize;
    color: var(--ods-black-900);
}

.review-who {
    color: var(--ods-gray-700);
}

.review-date {
    color: var(--ods-gray-500);
}

.review-comment {
    color: var(--ods-gray-700);
    font-style: italic;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 10rem;
}

.no-review {
    color: var(--ods-gray-400);
}

.confirm-row td {
    padding: 0;
    border-bottom: 0.125rem solid var(--ods-gray-300);
}

.confirm-panel {
    padding: 0.85rem 1.25rem 1rem;
    background: var(--ods-gray-200);
    border-top: 0.25rem solid var(--ods-orange-100);
}

.confirm-label {
    font-size: 0.875rem;
    color: var(--ods-gray-700);
    margin-bottom: 0.5rem;
    text-transform: capitalize;
}

.confirm-body {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
}

.comment-input {
    flex: 1;
    border: 0.125rem solid var(--ods-gray-300);
    border-radius: 0.25rem;
    padding: 0.45rem 0.75rem;
    font-size: 0.875rem;
    resize: vertical;
    outline: none;
    font-family: inherit;
    min-width: 0;
    transition: border-color 0.15s;
}

.comment-input:focus {
    border-color: var(--ods-orange-100);
    border-width: 0.15rem;
}

.confirm-actions {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    flex-shrink: 0;
}

.action-error {
    font-size: 0.75rem;
    color: var(--ods-black-900);
}

.action-btn.is-edit:hover,
.action-btn.is-edit.is-selected {
    background: var(--ods-gray-700);
    border-color: var(--ods-gray-700);
    color: var(--ods-white-100);
}

.edit-panel {
    border-top-color: var(--ods-gray-700);
}

.edit-fields {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}

.edit-field {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    flex: 1;
    min-width: 10rem;
}

.edit-field-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.125em;
    font-weight: 700;
    color: var(--ods-gray-700);
}

.edit-footer {
    display: flex;
    gap: 0.75rem;
    flex: 1;
    align-items: flex-start;
}

.edit-status-select {
    border: 0.125rem solid var(--ods-gray-300);
    border-radius: 0.25rem;
    padding: 0.375rem 0.65rem;
    font-size: 0.875rem;
    font-family: inherit;
    outline: none;
    flex-shrink: 0;
    transition: border-color 0.15s;
}

.edit-status-select:focus {
    border-color: var(--ods-orange-100);
}

.extractor-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
}

.extractor-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.125rem 0.35rem;
    border-radius: 0.25rem;
    background: var(--ods-gray-200);
    color: var(--ods-gray-700);
}

.extractor-dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 50%;
    flex-shrink: 0;
}

.text-panel {
    flex-shrink: 0;
    border-left: 0.125rem solid var(--ods-gray-300);
    background: var(--ods-white-100);
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: calc(100vh - 8rem);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.text-panel-resizer {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 0.375rem;
    cursor: col-resize;
    background: transparent;
    transition: background 0.15s;
    z-index: 1;
}

.text-panel-resizer:hover {
    background: var(--ods-orange-100);
}

.text-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    border-bottom: 0.125rem solid var(--ods-gray-200);
    flex-shrink: 0;
    flex-wrap: wrap;
}

.text-panel-title {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.125em;
    color: var(--ods-gray-500);
    font-weight: 700;
    white-space: nowrap;
}

.text-panel-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-left: auto;
}

.text-panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
}

.preview-legend {
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

.legend-chip {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.15rem 0.5rem;
    border-radius: 0.25rem;
}

.legend-chip.is-subject {
    background: rgba(8, 94, 189, 0.15);
    border-bottom: 0.15rem solid #085ebd;
    color: #085ebd;
}

.legend-chip.is-predicate {
    background: rgba(255, 121, 0, 0.15);
    border-bottom: 0.15rem solid var(--ods-orange-100);
    color: var(--ods-orange-100);
}

.legend-chip.is-object {
    background: rgba(34, 135, 34, 0.15);
    border-bottom: 0.15rem solid var(--ods-green-dark);
    color: var(--ods-green-dark);
}

.preview-toggle {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.25rem 0.65rem;
    border-radius: 2rem;
    border: 0.125rem solid var(--ods-gray-300);
    background: var(--ods-white-100);
    color: var(--ods-gray-700);
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
    white-space: nowrap;
}

.preview-toggle:hover {
    border-color: var(--ods-orange-100);
    color: var(--ods-orange-100);
}

.preview-toggle.is-active {
    background: var(--ods-orange-100);
    border-color: var(--ods-orange-100);
    color: var(--ods-white-100);
}

.preview-close {
    flex-shrink: 0;
    width: 2rem;
    height: 2rem;
    border: none;
    background: transparent;
    font-size: 1rem;
    cursor: pointer;
    color: var(--ods-gray-700);
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.25rem;
    transition: background 0.15s, color 0.15s;
}

.preview-close:hover {
    background: var(--ods-gray-200);
    color: var(--ods-orange-100);
}

.preview-state {
    padding: 2rem;
    text-align: center;
    color: var(--ods-gray-500);
    font-size: 0.875rem;
}

.preview-state-error {
    color: var(--ods-red-dark);
}

.preview-content {
    margin: 0;
    font-family: var(--bs-font-monospace);
    font-size: 0.75rem;
    line-height: 1.75;
    color: var(--ods-black-900);
    white-space: pre-wrap;
    word-break: break-word;
}

.hl-subject {
    background: rgba(8, 94, 189, 0.15);
    border-bottom: 0.15rem solid #085ebd;
    border-radius: 0.15rem;
}

.hl-predicate {
    background: rgba(255, 121, 0, 0.15);
    border-bottom: 0.15rem solid var(--ods-orange-100);
    border-radius: 0.15rem;
}

.hl-object {
    background: rgba(34, 135, 34, 0.15);
    border-bottom: 0.15rem solid var(--ods-green-dark);
    border-radius: 0.15rem;
}

@media (max-width: 1200px) {
    .file-sidebar {
        width: 10rem;
    }

    .table-wrapper {
        padding: 1.25rem 1.5rem 1.5rem;
    }

    .page-intro {
        padding: 1.5rem 1.5rem 1rem;
    }
}

@media (max-width: 992px) {
    .file-sidebar {
        width: 8.5rem;
    }

    .val-toolbar {
        padding: 0.75rem 1.25rem;
    }

    .table-wrapper {
        padding: 1rem 1.25rem 1.5rem;
    }

    .edit-fields {
        flex-direction: column;
    }
}

@media (max-width: 768px) {
    .val-body {
        flex-direction: column;
    }

    .file-sidebar {
        width: 100%;
        border-right: none;
        border-bottom: 0.125rem solid var(--ods-gray-300);
        position: static;
        max-height: 12rem;
        padding: 1rem 1.25rem;
    }

    .file-list {
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
    }

    .page-intro {
        padding: 1rem;
    }

    .val-toolbar {
        padding: 0.5rem 1rem;
    }

    .table-wrapper {
        padding: 0.75rem 1rem 1rem;
    }
}

.danger-zone {
    margin: 2.5rem 1.5rem 2rem;
    padding: 1.25rem 1.5rem;
    border: 0.0625rem solid var(--ods-red-dark);
    border-radius: 0.5rem;
    background: rgba(205, 60, 20, 0.04);
}

.danger-header {
    margin-bottom: 1rem;
}

.danger-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--ods-red-dark);
    margin: 0 0 0.25rem;
}

.danger-subtitle {
    font-size: 0.85rem;
    color: var(--ods-gray-700);
    margin: 0;
    max-width: 46rem;
}

.danger-actions,
.danger-confirm-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.danger-confirm-text {
    font-size: 0.9rem;
    color: var(--ods-black-900);
    margin: 0 0 0.75rem;
}

.danger-confirm-label {
    display: block;
    font-size: 0.8rem;
    color: var(--ods-gray-700);
    margin-bottom: 0.35rem;
}

.danger-confirm-input {
    width: 12rem;
    max-width: 100%;
    padding: 0.35rem 0.6rem;
    border: 0.0625rem solid var(--ods-red-dark);
    border-radius: 0.3rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    letter-spacing: 0.1em;
    margin-bottom: 0.85rem;
}

.danger-confirm-input:focus {
    outline: none;
    box-shadow: 0 0 0 0.15rem rgba(205, 60, 20, 0.25);
}

.btn-danger-outline {
    background: transparent;
    border: 0.0625rem solid var(--ods-red-dark);
    color: var(--ods-red-dark);
}

.btn-danger-outline:hover:not(:disabled) {
    background: var(--ods-red-dark);
    color: var(--ods-white-100);
}

.btn-danger {
    background: var(--ods-red-dark);
    border: 0.0625rem solid var(--ods-red-dark);
    color: var(--ods-white-100);
}

.btn-danger:hover:not(:disabled) {
    background: #b23411;
    border-color: #b23411;
}

.reset-done {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--ods-green-dark);
}

.danger-name-missing {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--ods-red-dark);
}

.files-modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 1rem;
}

.files-modal {
    --ods-orange-100: #ff7900;
    --ods-white-100: #fff;
    --ods-gray-300: #ddd;
    --ods-gray-700: #595959;
    --ods-black-900: #000;
    --ods-red-dark: #cd3c14;
    background: var(--ods-white-100);
    border-radius: 0.5rem;
    width: min(40rem, 100%);
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    padding: 1.5rem;
    box-shadow: 0 0.5rem 2rem rgba(0, 0, 0, 0.25);
}

.files-modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
}

.files-modal-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0;
}

.files-modal-warning {
    font-size: 0.85rem;
    color: var(--ods-red-dark);
    margin: 0 0 0.75rem;
}

.files-modal-list {
    list-style: none;
    padding: 0;
    margin: 0;
    overflow-y: auto;
}

.files-modal-empty {
    color: var(--ods-gray-700);
    font-size: 0.9rem;
    padding: 1rem 0;
}

.files-modal-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem 0;
    border-bottom: 0.0625rem solid var(--ods-gray-300);
}

.files-modal-info {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
}

.files-modal-name {
    font-weight: 600;
    font-size: 0.9rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.files-modal-meta {
    font-size: 0.75rem;
    color: var(--ods-gray-700);
}

.files-modal-confirm {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
    flex-shrink: 0;
}
</style>
