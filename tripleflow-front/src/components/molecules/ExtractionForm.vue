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
    <div class="mb-4">
        <div class="mb-3">
            <label class="form-label fw-bold mb-2">Extractors</label>

            <div class="d-flex gap-3 flex-wrap">
                <div
                    v-for="option in extractorOptions"
                    :key="option.value"
                    class="form-check"
                >
                    <input
                        :id="`extractor-${option.value}`"
                        class="form-check-input"
                        type="checkbox"
                        :value="option.value"
                        :checked="extractors.includes(option.value)"
                        @change="toggleExtractor(option.value)"
                    />
                    <label class="form-check-label" :for="`extractor-${option.value}`">
                        {{ option.label }}
                    </label>
                </div>
            </div>

            <p v-if="extractorOptions.length === 0" class="small text-muted mt-2 mb-0">
                No extractors are available on this instance — add one from the Extractors page.
            </p>
            <p v-else class="small text-muted mt-2 mb-0">Select one or more extractors</p>
        </div>

        <div class="mb-3">
            <label for="input-file" class="form-label fw-bold mb-2">Upload .txt or .pdf files</label>

            <div
                class="upload-dropzone"
                :class="{ 'is-dragging': isDragging }"
                @dragenter.prevent="isDragging = true"
                @dragover.prevent="isDragging = true"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
            >
                <input
                    ref="fileInputRef"
                    id="input-file"
                    class="visually-hidden"
                    type="file"
                    accept=".txt,.pdf,text/plain,application/pdf"
                    multiple
                    @change="handleInputChange"
                />
                <input
                    ref="folderInputRef"
                    class="visually-hidden"
                    type="file"
                    webkitdirectory
                    directory
                    multiple
                    @change="handleFolderChange"
                />

                <div class="upload-icon" aria-hidden="true">
                    <svg class="upload-file-icon" width="960" height="960" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M625,75V225c0,27.614,19.9,50,44.444,50H825Zm50,250a100,100,0,0,1-100-100V75H175V874.773h0.006c0,0.076-.006.151-0.006,0.227a50,50,0,0,0,50,50H825V325H675ZM325,375H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,375Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,475Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,575ZM425,725H325a25,25,0,0,1,0-50H425A25,25,0,0,1,425,725Z" transform="scale(.96)" fill="currentColor"/></svg>
                    <svg class="upload-file-icon second-file" width="960" height="960" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M625,75V225c0,27.614,19.9,50,44.444,50H825Zm50,250a100,100,0,0,1-100-100V75H175V874.773h0.006c0,0.076-.006.151-0.006,0.227a50,50,0,0,0,50,50H825V325H675ZM325,375H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,375Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,475Zm0,100H675a25,25,0,0,1,0,50H325A25,25,0,0,1,325,575ZM425,725H325a25,25,0,0,1,0-50H425A25,25,0,0,1,425,725Z" transform="scale(.96)" fill="currentColor"/></svg>
                </div>

                <p class="upload-title mb-2">Drop files or choose a folder</p>

                <div class="upload-actions">
                    <Button
                        variant="primary"
                        extraClass="upload-browse-button"
                        @click="openFilePicker"
                    >
                        Browse files
                    </Button>

                    <Button
                        variant="outline-secondary"
                        extraClass="upload-browse-button"
                        @click="openFolderPicker"
                    >
                        Browse folder
                    </Button>
                </div>
            </div>

            <p v-if="fileName && fileTextInputs.length === 0" class="small text-muted mt-2 mb-0">Loaded files: {{ fileName }}</p>
        </div>

        <div v-if="fileTextInputs.length > 0" class="mb-3">
            <div
                ref="inputsScrollerRef"
                class="file-text-inputs-scroller"
            >
                <div
                    v-for="(fileTextInput, index) in fileTextInputs"
                    :key="fileTextInput.fileKey"
                    class="file-text-input mb-3"
                    :class="{ 'is-source-highlighted': highlightedInputIndex === index }"
                    :data-input-index="index"
                >
                    <template v-if="isManualInput(fileTextInput)">
                        <div class="manual-input-header mb-2">
                            <div class="manual-input-label-row">
                                <button
                                    type="button"
                                    class="manual-rename-btn"
                                    :title="`Rename ${fileTextInput.name}`"
                                    @click.stop="startRename(index, fileTextInput.name)"
                                >
                                    <svg width="12" height="12" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path fill-rule="evenodd" d="M880,192L768,80a50,50,0,0,0-70.711,0L160,617.289V800H342.711L880,262.711A50,50,0,0,0,880,192ZM316,750H210V644l422-422,106,106Zm464-523L674,121l56-56,106,106Z" fill="currentColor"/></svg>
                                </button>
                                <input
                                    v-if="renamingIndex === index"
                                    v-focus
                                    type="text"
                                    class="manual-rename-input"
                                    :value="renameValue"
                                    @input="renameValue = $event.target.value"
                                    @blur="confirmRename(index)"
                                    @keydown.enter="$event.target.blur()"
                                    @keydown.escape="cancelRename"
                                    @click.stop
                                />
                                <label v-else :for="`input-file-text-${index}`" class="form-label fw-bold mb-0">
                                    {{ fileTextInput.name }}
                                </label>
                            </div>
                            <button
                                type="button"
                                class="manual-remove-btn"
                                :aria-label="`Remove ${fileTextInput.name}`"
                                @click="removeSingleFile(index)"
                            >✕</button>
                        </div>
                    </template>

                    <template v-else>
                        <div class="uploaded-file-item mb-2">
                            <button
                                type="button"
                                class="file-preview-button"
                                :aria-label="`Remove ${fileTextInput.name}`"
                                @click="removeSingleFile(index)"
                            >
                                <img
                                    src="/icons/file-cancelled.png"
                                    :alt="`Remove ${fileTextInput.name}`"
                                    class="file-item-image"
                                >
                            </button>
                            <label :for="`input-file-text-${index}`" class="form-label fw-bold mb-0">
                                {{ fileTextInput.name }}
                            </label>
                        </div>
                    </template>

                    <Textarea
                        :id="`input-file-text-${index}`"
                        :modelValue="fileTextInput.text"
                        @update:modelValue="updateFileTextAndClearError(index, $event)"
                        :rows="8"
                        :placeholder="fileTextInput.fileKey.startsWith('manual-') ? 'Enter your text...' : 'File text will appear here...'"
                        :class="{ 'is-invalid': emptyInputIndices.has(index) }"
                    />
                    <p v-if="emptyInputIndices.has(index)" class="input-error-msg">
                        This field is required.
                    </p>
                </div>
            </div>

            <button
                type="button"
                class="add-input-button"
                :disabled="disabled"
                @click="emit('add:manual-input')"
            >
                + Add text input
            </button>
        </div>

        <div v-else class="mb-3">
            <div
                class="text-input-block"
                :class="{ 'is-source-highlighted': highlightedInputIndex === 0 }"
                data-input-index="0"
            >
                <div class="manual-input-header mb-2">
                    <div class="manual-input-label-row">
                        <button
                            type="button"
                            class="manual-rename-btn"
                            title="Rename"
                            :disabled="disabled"
                            @click="convertAndRename"
                        >
                            <svg width="12" height="12" viewBox="0 0 960 960" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path fill-rule="evenodd" d="M880,192L768,80a50,50,0,0,0-70.711,0L160,617.289V800H342.711L880,262.711A50,50,0,0,0,880,192ZM316,750H210V644l422-422,106,106Zm464-523L674,121l56-56,106,106Z" fill="currentColor"/></svg>
                        </button>
                        <label for="input-text" class="form-label fw-bold mb-0">Input text</label>
                    </div>
                </div>

                <Textarea
                    id="input-text"
                    :modelValue="modelValue"
                    @update:modelValue="onInput"
                    :rows="10"
                    placeholder="Enter your text to extract triples..."
                />
            </div>

            <button
                type="button"
                class="add-input-button"
                :disabled="disabled"
                @click="emit('add:manual-input')"
            >
                + Add text input
            </button>
        </div>

        <div class="d-flex gap-2">
            <Button
                variant="primary"
                :disabled="disabled || extractors.length === 0"
                @click="validateAndSubmit"
            >
                Run extraction
            </Button>

            <Button
                variant="outline-secondary"
                :disabled="disabled"
                @click="emit('clear:text')"
            >
                Clear input
            </Button>
        </div>
    </div>
</template>

<script setup>
/**
 * Form for configuring and launching a triple extraction.
 * Handles extractor selection, file and folder upload (with drag-and-drop support),
 * per-file text editing, manual text input, and the Run/Clear actions.
 */
import { nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import Button from '../atoms/Button.vue'
import Textarea from '../atoms/Textarea.vue'

const props = defineProps({
    modelValue: {
        type: String,
        default: '',
    },
    extractors: {
        type: Array,
        default: () => [],
    },
    extractorOptions: {
        type: Array,
        default: () => [],
    },
    fileName: {
        type: String,
        default: '',
    },
    files: {
        type: Array,
        default: () => [],
    },
    fileTextInputs: {
        type: Array,
        default: () => [],
    },
    disabled: {
        type: Boolean,
        default: false,
    },
    highlightedInputIndex: {
        type: Number,
        default: null,
    },
})

const emit = defineEmits([
    'update:modelValue',
    'update:extractors',
    'update:file',
    'update:file-text',
    'update:input-name',
    'remove:file',
    'add:manual-input',
    'convert:to-manual',
    'clear:text',
    'submit',
])

const fileInputRef = ref(null)
const folderInputRef = ref(null)
const inputsScrollerRef = ref(null)
const isDragging = ref(false)
const renamingIndex = ref(null)
const renameValue = ref('')
const emptyInputIndices = ref(new Set())
const pendingRenameOnConvert = ref(false)

const vFocus = { mounted: (el) => el.focus() }

function isManualInput(fileTextInput) {
    return fileTextInput.fileKey.startsWith('manual-')
}

function startRename(index, currentName) {
    renamingIndex.value = index
    renameValue.value = currentName
}

function confirmRename(index) {
    const trimmed = renameValue.value.trim()
    renamingIndex.value = null
    if (!trimmed || trimmed === props.fileTextInputs[index]?.name) return
    emit('update:input-name', { index, name: trimmed })
}

function cancelRename() {
    renamingIndex.value = null
}

function convertAndRename() {
    pendingRenameOnConvert.value = true
    emit('convert:to-manual')
}

/** Programmatically opens the hidden file input dialog. */
function openFilePicker() {
    if (!props.disabled) {
        fileInputRef.value?.click()
    }
}

/** Programmatically opens the hidden folder input dialog. */
function openFolderPicker() {
    if (!props.disabled) {
        folderInputRef.value?.click()
    }
}

/** Emits 'update:file' when the user selects files via the file input, then resets the input. */
function handleInputChange(event) {
    const files = Array.from(event.target.files || [])
    emit('update:file', files.length > 0 ? files : null)
    event.target.value = ''
}

/** Emits 'update:file' when the user selects a folder, then resets the input. */
function handleFolderChange(event) {
    const files = Array.from(event.target.files || [])
    emit('update:file', files.length > 0 ? files : null)
    event.target.value = ''
}

/** Handles a drag-and-drop file drop onto the upload zone and emits the dropped files. */
function handleDrop(event) {
    isDragging.value = false

    if (props.disabled) {
        return
    }

    const files = Array.from(event.dataTransfer?.files || [])
    emit('update:file', files.length > 0 ? files : null)
}

/** Clears the dragging state only when the cursor leaves the drop zone element itself, not a child. */
function handleDragLeave(event) {
    if (event.currentTarget === event.target) {
        isDragging.value = false
    }
}

/** Emits 'remove:file' with the file index to remove a single uploaded file. */
function removeSingleFile(index) {
    emit('remove:file', index)
}

/** Forwards the textarea value to the parent via 'update:modelValue'. */
function onInput(value) {
    emit('update:modelValue', value)
}

/** Emits 'update:file-text' when the user edits the text content of a loaded file. */
function updateFileText(index, value) {
    emit('update:file-text', { index, value })
}

/** Updates the file text and clears the empty-field error for that index if the user has typed something. */
function updateFileTextAndClearError(index, value) {
    if (value.trim() && emptyInputIndices.value.has(index)) {
        const next = new Set(emptyInputIndices.value)
        next.delete(index)
        emptyInputIndices.value = next
    }
    emit('update:file-text', { index, value })
}

/** Validates that no file/manual text inputs are empty before submitting. Shows inline errors if any are. */
function validateAndSubmit() {
    if (props.fileTextInputs.length > 0) {
        const empty = new Set(
            props.fileTextInputs
                .map((entry, i) => (!entry.text.trim() ? i : null))
                .filter((i) => i !== null)
        )
        emptyInputIndices.value = empty
        if (empty.size > 0) return
    }
    emptyInputIndices.value = new Set()
    emit('submit')
}

/** Adds or removes an extractor from the selected list and emits 'update:extractors'. */
function toggleExtractor(value) {
    const updated = props.extractors.includes(value)
        ? props.extractors.filter((item) => item !== value)
        : [...props.extractors, value]

    emit('update:extractors', updated)
}

function getFileLabel(file) {
    return file?.webkitRelativePath || file?.name || ''
}

watch(
    () => props.fileTextInputs.length,
    async (newLen) => {
        await nextTick()
        if (pendingRenameOnConvert.value && newLen > 0) {
            pendingRenameOnConvert.value = false
            startRename(0, props.fileTextInputs[0].name)
        }
    },
    { immediate: true }
)

watch(
    () => props.highlightedInputIndex,
    async () => {
        await nextTick()
    }
)
</script>

<style scoped>
.upload-dropzone,
.upload-icon,
.upload-title,
.file-preview-button:focus-visible,
.file-item-name,
.file-text-input,
.text-input-block {
    --ods-orange-100: #ff7900;
    --ods-white-100: #fff;
    --ods-gray-300: #ddd;
    --ods-gray-700: #595959;
    --ods-black-900: #000;
}

.upload-dropzone {
    border: 0.1rem dashed var(--ods-gray-300);
    border-radius: 0.75rem;
    padding: 1.5rem 1rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    background: var(--ods-white-100);
    transition: border-color 0.2s ease, background-color 0.2s ease;
}

.upload-dropzone.is-dragging {
    border-color: var(--ods-orange-100);
    background: var(--ods-white-100);
}

.upload-icon {
    position: relative;
    font-size: 2.5rem;
    color: var(--ods-black-900);
    line-height: 1;
    height: 3.5rem;
    width: 3.5rem;
}

.upload-icon .upload-file-icon {
    position: absolute;
    width: 2.5rem;
    height: 2.5rem;
}

.upload-icon .second-file {
    left: 0.5rem;
    top: 0.35rem;
    opacity: 0.7;
}

.upload-title {
    font-size: 1rem;
    font-weight: 500;
    color: var(--ods-black-900);
}

.upload-browse-button {
    min-width: 12rem;
}

.upload-actions {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    justify-content: center;
}

.uploaded-files {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.uploaded-file-item {
    width: 5rem;
    padding-top: 0.25rem;
    text-align: center;
}

.file-preview-button {
    border: none;
    background: transparent;
    padding: 0;
    cursor: pointer;
}

.file-item-image {
    display: block;
    width: 3rem;
    height: auto;
    margin: 0 auto 0.5rem;
}

.file-preview-button:hover .file-item-image {
    transform: scale(1.05);
}

.file-preview-button:focus-visible {
    outline: 0.125rem solid var(--ods-orange-100);
    outline-offset: 0.25rem;
    border-radius: 0.5rem;
}

.file-item-name {
    display: block;
    font-size: 0.75rem;
    line-height: 1.2;
    color: var(--ods-gray-700);
    word-break: break-word;
}

.file-text-input:last-child {
    margin-bottom: 0;
}

.file-text-inputs-scroller {
    max-height: 34rem;
    overflow-y: auto;
    padding-right: 0.35rem;
    scroll-behavior: smooth;
}

.file-text-inputs-scroller::-webkit-scrollbar {
    width: 0.45rem;
}

.file-text-inputs-scroller::-webkit-scrollbar-thumb {
    background: var(--ods-gray-300);
    border-radius: 999px;
}

.file-text-inputs-scroller::-webkit-scrollbar-track {
    background: #eee;
    border-radius: 999px;
}

.file-text-input,
.text-input-block {
    border-radius: 0.9rem;
    transition: background-color 0.25s ease, box-shadow 0.25s ease;
}

.is-source-highlighted {
    animation: sourcePulse 1.2s ease;
}

@keyframes sourcePulse {
    0% {
        background-color: transparent;
        box-shadow: 0 0 0 0 rgba(255, 121, 0, 0);
    }
    25% {
        background-color: rgba(255, 121, 0, 0.09);
        box-shadow: 0 0 0 0.2rem rgba(255, 121, 0, 0.18);
    }
    100% {
        background-color: transparent;
        box-shadow: 0 0 0 0 rgba(255, 121, 0, 0);
    }
}

.add-input-button {
    --ods-orange-100: #ff7900;
    --ods-gray-300: #ddd;
    --ods-gray-700: #595959;

    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    margin-top: 0.25rem;
    padding: 0.3rem 0.85rem;
    border: 0.1rem dashed var(--ods-gray-300);
    border-radius: 0.4rem;
    background: transparent;
    color: var(--ods-gray-700);
    font-size: 0.85rem;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
}

.add-input-button:hover:not(:disabled) {
    border-color: var(--ods-orange-100);
    color: var(--ods-orange-100);
}

.add-input-button:disabled {
    opacity: 0.5;
    cursor: default;
}

.manual-input-header {
    --ods-orange-100: #ff7900;
    --ods-gray-500: #999;

    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
}

.manual-input-label-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    min-width: 0;
}

.manual-rename-btn {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    border: none;
    background: transparent;
    padding: 0.1rem;
    cursor: pointer;
    color: var(--ods-gray-500);
    border-radius: 0.2rem;
    line-height: 1;
    transition: color 0.15s;
}

.manual-rename-btn:hover {
    color: var(--ods-orange-100);
}

.manual-remove-btn {
    flex-shrink: 0;
    border: none;
    background: transparent;
    padding: 0.1rem 0.3rem;
    cursor: pointer;
    color: var(--ods-gray-500);
    font-size: 0.75rem;
    border-radius: 0.2rem;
    line-height: 1;
    transition: color 0.15s;
}

.manual-remove-btn:hover {
    color: #cd3c14;
}

.input-error-msg {
    margin: 0.35rem 0 0;
    font-size: 0.8rem;
    color: #cd3c14;
    font-weight: 600;
}

.manual-rename-input {
    flex: 1;
    min-width: 0;
    border: none;
    border-bottom: 0.1rem solid var(--ods-orange-100);
    background: transparent;
    font-size: 0.9rem;
    font-weight: 700;
    padding: 0 0 0.1rem;
    outline: none;
    color: inherit;
    font-family: inherit;
}
</style>
