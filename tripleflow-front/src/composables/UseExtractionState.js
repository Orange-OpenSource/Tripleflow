/*  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

*/

import { computed, onBeforeUnmount, ref } from 'vue'

import { fetchExtraction } from './extraction/api'
import {
    BACKEND_ERROR_PREFIX,
    EXTRACTOR_REQUIRED_ERROR,
    FILE_READ_ERROR,
    INPUT_REQUIRED_ERROR,
    SUPPORTED_FILE_ERROR,
} from './extraction/constants'
import {
    buildFileKey,
    buildSelectedFileName,
    buildTextFromEntries,
    isPdfFile,
    isSameFile,
    isTxtFile,
    readFileText,
} from './extraction/fileText'
import { normalizeTriples } from './extraction/normalizers'

let extractionState = null
let activeConsumersCount = 0

/** Returns a blank result object with no loading state, no triples, and no error. */
function createInitialResult() {
    return {
        loadingByExtractor: {},
        result: {},
        error: '',
    }
}

/**
 * Builds the extraction request payload from the current text and file inputs.
 * Uses the batch form (texts[]) when more than one file is loaded.
 * @param {string} text - combined text value
 * @param {{ name: string, text: string }[]} fileTextInputs
 * @returns {{ text: string, texts: string[], file_name?: string|null, file_names?: (string|null)[] }}
 */
function getRequestPayload(text, fileTextInputs) {
    const validInputs = Array.isArray(fileTextInputs)
        ? fileTextInputs.filter((entry) => typeof entry?.text === 'string' && entry.text.trim())
        : []

    const sanitizedTexts = validInputs.map((entry) => entry.text.trim())

    if (sanitizedTexts.length > 1) {
        return {
            text,
            texts: sanitizedTexts,
            file_names: validInputs.map((entry) => entry.name || null),
        }
    }

    return {
        text,
        texts: [],
        file_name: validInputs[0]?.name || null,
    }
}

/**
 * Collects error messages from items that failed in a batch extraction response.
 * Returns an empty string if all items succeeded.
 * @param {object} data - raw API response body
 * @returns {string}
 */
function buildPartialExtractionError(data) {
    const items = Array.isArray(data?.result?.items) ? data.result.items : []
    const failedItems = items.filter((item) => item?.status === 'error')

    if (failedItems.length === 0) {
        return ''
    }

    return failedItems
        .map((item) => {
            const label = typeof item?.index === 'number' ? `Input ${item.index + 1}` : 'Input'
            const message = item?.error?.trim?.() || 'Unknown extraction error.'
            return `${label}: ${message}`
        })
        .join(' | ')
}

/**
 * Builds the list of source descriptors used to label where each extracted triple came from.
 * Each source has an index, label, name, and type ('file' or 'text').
 * @param {string} rawText
 * @param {{ name: string }[]} fileTextInputs
 * @returns {{ index: number, label: string, name: string, type: string }[]}
 */
function buildInputSources(rawText, fileTextInputs) {
    if (Array.isArray(fileTextInputs) && fileTextInputs.length > 0) {
        return fileTextInputs.map((entry, index) => ({
            index,
            label: entry?.name || `Input ${index + 1}`,
            name: entry?.name || '',
            type: 'file',
        }))
    }

    if (typeof rawText === 'string' && rawText.trim() !== '') {
        return [{
            index: 0,
            label: 'Input text',
            name: '',
            type: 'text',
        }]
    }

    return []
}

/**
 * Creates the full reactive extraction state: input text, selected files, extractor list,
 * per-extractor loading/timing/error state, and all action functions.
 * This is called once and shared across all consumers via useExtractionState().
 */
function createExtractionState() {
    const rawText = ref('')
    const fileTextInputs = ref([])

    // No default selection: the available extractors are instance-specific and
    // served by the backend, so the user picks one once the list is loaded.
    const selectedExtractors = ref([])
    const selectedFiles = ref([])
    const selectedFileName = ref('')

    const result = ref(createInitialResult())
    const elapsedTime = ref(0)
    const finalTime = ref(null)
    const extractorElapsedTimes = ref({})
    const extractorFinalTimes = ref({})
    const extractorErrors = ref({})
    const timers = new Map()

    const text = computed({
        get: () => {
            if (fileTextInputs.value.length > 0) {
                return buildTextFromEntries(fileTextInputs.value)
            }

            return rawText.value
        },
        set: (value) => {
            rawText.value = value
        },
    })

    const loadingByExtractor = computed(() => result.value.loadingByExtractor)

    const isLoading = computed(() => {
        return selectedExtractors.value.some((extractor) => loadingByExtractor.value[extractor] === true)
    })

    const errorMessage = computed(() => result.value.error)

    const triples = computed(() => {
        if (result.value.error) {
            return {}
        }

        return result.value.result
    })

    function clearTimers() {
        timers.forEach((timerId) => clearInterval(timerId))
        timers.clear()
    }

    function resetTimingState() {
        extractorElapsedTimes.value = {}
        extractorFinalTimes.value = {}
        elapsedTime.value = 0
        finalTime.value = null
    }

    function resetInputState() {
        rawText.value = ''
        fileTextInputs.value = []
        selectedFiles.value = []
        selectedFileName.value = ''
    }

    function resetExtractionFeedback() {
        clearTimers()
        resetTimingState()
        extractorErrors.value = {}
        result.value = createInitialResult()
    }

    function setGlobalError(message) {
        result.value = {
            ...createInitialResult(),
            error: message,
        }
    }

    function updateExtractors(value) {
        selectedExtractors.value = Array.isArray(value) ? [...new Set(value)] : []
    }

    function syncAggregateTimes() {
        const elapsedValues = Object.values(extractorElapsedTimes.value)
        const finalValues = Object.values(extractorFinalTimes.value).filter((value) => value !== null && value !== undefined)

        elapsedTime.value = elapsedValues.length > 0 ? Math.max(...elapsedValues) : 0
        finalTime.value = finalValues.length > 0 ? Math.max(...finalValues) : null
    }

    function startExtractorTimer(extractor) {
        const existingTimer = timers.get(extractor)
        if (existingTimer) {
            clearInterval(existingTimer)
        }

        extractorElapsedTimes.value = {
            ...extractorElapsedTimes.value,
            [extractor]: 0,
        }
        extractorFinalTimes.value = {
            ...extractorFinalTimes.value,
            [extractor]: null,
        }

        syncAggregateTimes()

        const timerId = setInterval(() => {
            extractorElapsedTimes.value = {
                ...extractorElapsedTimes.value,
                [extractor]: (extractorElapsedTimes.value[extractor] || 0) + 1,
            }
            syncAggregateTimes()
        }, 1000)

        timers.set(extractor, timerId)
    }

    function stopExtractorTimer(extractor) {
        const timerId = timers.get(extractor)

        if (timerId) {
            clearInterval(timerId)
            timers.delete(extractor)
        }

        extractorFinalTimes.value = {
            ...extractorFinalTimes.value,
            [extractor]: extractorElapsedTimes.value[extractor] || 0,
        }

        syncAggregateTimes()
    }

    function buildLoadingState(extractors, isExtractorLoading) {
        return extractors.reduce((accumulator, extractor) => {
            accumulator[extractor] = isExtractorLoading
            return accumulator
        }, {})
    }

    function setExtractorLoading(extractor, isExtractorLoading) {
        result.value = {
            ...result.value,
            loadingByExtractor: {
                ...result.value.loadingByExtractor,
                [extractor]: isExtractorLoading,
            },
        }
    }

    function setExtractorResult(extractor, extractorTriples) {
        result.value = {
            ...result.value,
            result: {
                ...result.value.result,
                [extractor]: extractorTriples,
            },
        }
    }

    function setExtractorError(extractor, error) {
        extractorErrors.value = {
            ...extractorErrors.value,
            [extractor]: error,
        }
    }

    const MANUAL_KEY_PREFIX = 'manual-'

    function isManualEntry(entry) {
        return entry.fileKey.startsWith(MANUAL_KEY_PREFIX)
    }

    async function syncTextFromSelectedFiles(files) {
        const manualEntries = fileTextInputs.value.filter(isManualEntry)

        if (files.length === 0) {
            fileTextInputs.value = manualEntries
            rawText.value = buildTextFromEntries(manualEntries)
            return
        }

        const currentEntries = new Map(
            fileTextInputs.value.map((entry) => [entry.fileKey, entry])
        )

        const nextEntries = []

        for (const file of files) {
            const fileKey = buildFileKey(file)
            const existingEntry = currentEntries.get(fileKey)

            if (existingEntry) {
                nextEntries.push(existingEntry)
                continue
            }

            nextEntries.push({
                fileKey,
                name: file.name,
                text: await readFileText(file),
            })
        }

        const allEntries = [...nextEntries, ...manualEntries]
        fileTextInputs.value = allEntries
        rawText.value = buildTextFromEntries(allEntries)
    }

    async function handleFileUpload(files) {
        if (!files || files.length === 0) {
            return
        }

        const supportedFiles = files.filter((file) => isTxtFile(file) || isPdfFile(file))
        if (supportedFiles.length === 0) {
            setGlobalError(SUPPORTED_FILE_ERROR)
            return
        }

        const mergedFiles = [...selectedFiles.value]
        supportedFiles.forEach((file) => {
            if (!mergedFiles.some((existingFile) => isSameFile(existingFile, file))) {
                mergedFiles.push(file)
            }
        })

        selectedFiles.value = mergedFiles
        selectedFileName.value = buildSelectedFileName(mergedFiles)

        try {
            resetExtractionFeedback()
            await syncTextFromSelectedFiles(mergedFiles)
        } catch {
            resetInputState()
            setGlobalError(FILE_READ_ERROR)
        }
    }

    function clearText() {
        resetExtractionFeedback()
        resetInputState()
    }

    function updateFileText(index, value) {
        if (index < 0 || index >= fileTextInputs.value.length) {
            return
        }

        fileTextInputs.value = fileTextInputs.value.map((entry, entryIndex) => (
            entryIndex === index
                ? { ...entry, text: value }
                : entry
        ))
    }

    function updateInputName(index, name) {
        if (index < 0 || index >= fileTextInputs.value.length) {
            return
        }

        fileTextInputs.value = fileTextInputs.value.map((entry, entryIndex) => (
            entryIndex === index
                ? { ...entry, name }
                : entry
        ))
    }

    function addManualInput() {
        const nextCount = fileTextInputs.value.filter(isManualEntry).length + 1

        if (fileTextInputs.value.length === 0 && rawText.value.trim()) {
            const firstKey = `${MANUAL_KEY_PREFIX}${Date.now()}`
            const secondKey = `${MANUAL_KEY_PREFIX}${Date.now() + 1}`
            fileTextInputs.value = [
                { fileKey: firstKey, name: 'Manual input 1', text: rawText.value },
                { fileKey: secondKey, name: 'Manual input 2', text: '' },
            ]
        } else {
            const key = `${MANUAL_KEY_PREFIX}${Date.now()}`
            fileTextInputs.value = [
                ...fileTextInputs.value,
                { fileKey: key, name: `Manual input ${nextCount}`, text: '' },
            ]
        }

        rawText.value = buildTextFromEntries(fileTextInputs.value)
    }

    function convertToManualInput() {
        const key = `${MANUAL_KEY_PREFIX}${Date.now()}`
        fileTextInputs.value = [
            { fileKey: key, name: 'Manual input 1', text: rawText.value },
        ]
        rawText.value = buildTextFromEntries(fileTextInputs.value)
    }

    async function removeFile(index = null) {
        resetExtractionFeedback()

        if (index === null || index === undefined) {
            resetInputState()
            return
        }

        const entry = fileTextInputs.value[index]
        if (!entry) return

        const updatedTextInputs = fileTextInputs.value.filter((_, i) => i !== index)
        fileTextInputs.value = updatedTextInputs
        rawText.value = buildTextFromEntries(updatedTextInputs)

        if (!isManualEntry(entry)) {
            const updatedFiles = selectedFiles.value.filter(
                (f) => buildFileKey(f) !== entry.fileKey
            )
            selectedFiles.value = updatedFiles
            selectedFileName.value = buildSelectedFileName(updatedFiles)
        }
    }

    async function runExtractor(extractor) {
        startExtractorTimer(extractor)
        setExtractorLoading(extractor, true)

        try {
            const requestStartedAt = new Date().toISOString()
            const requestPayload = getRequestPayload(text.value, fileTextInputs.value)
            const inputSources = buildInputSources(rawText.value, fileTextInputs.value)
            const extractionResponse = await fetchExtraction({
                extractor,
                text: requestPayload.text,
                texts: requestPayload.texts,
                file_name: requestPayload.file_name,
                file_names: requestPayload.file_names,
            })
            const data = extractionResponse?.data
            const extractionTimestamp = extractionResponse?.responseTimestamp || requestStartedAt
            const normalizedTriples = normalizeTriples(data, {
                inputSources,
                extractionTimestamp,
            })
            const partialError = buildPartialExtractionError(data)

            setExtractorResult(extractor, normalizedTriples)
            if (partialError) {
                setExtractorError(extractor, partialError)
            }

            return {
                extractor,
                success: true,
                triples: normalizedTriples,
                error: partialError,
            }
        } catch (error) {
            const message = error.message || `${BACKEND_ERROR_PREFIX} ${extractor}.`
            setExtractorError(extractor, message)

            return {
                extractor,
                success: false,
                error: message,
            }
        } finally {
            stopExtractorTimer(extractor)
            setExtractorLoading(extractor, false)
        }
    }

    async function runExtraction() {
        if (text.value.trim() === '' && selectedFiles.value.length === 0) {
            setGlobalError(INPUT_REQUIRED_ERROR)
            return
        }

        if (selectedExtractors.value.length === 0) {
            setGlobalError(EXTRACTOR_REQUIRED_ERROR)
            return
        }

        resetExtractionFeedback()
        result.value = {
            ...createInitialResult(),
            loadingByExtractor: buildLoadingState(selectedExtractors.value, true),
        }

        try {
            const responses = await Promise.all(
                selectedExtractors.value.map((extractor) => runExtractor(extractor))
            )
            const successfulExtractions = responses.filter((item) => item.success)

            result.value = {
                loadingByExtractor: buildLoadingState(selectedExtractors.value, false),
                result: result.value.result,
                error: successfulExtractions.length === 0
                    ? responses.map((item) => item.error).filter(Boolean).join(' | ')
                    : '',
            }
        } catch (error) {
            result.value = {
                ...createInitialResult(),
                loadingByExtractor: buildLoadingState(selectedExtractors.value, false),
                error: error.message || 'Error contacting backend.',
            }
        }
    }

    function release() {
        clearTimers()
    }

    return {
        text,
        fileTextInputs,
        selectedFiles,
        selectedExtractors,
        selectedFileName,
        result,
        loadingByExtractor,
        elapsedTime,
        finalTime,
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
        release,
    }
}

/**
 * Vue composable that returns the shared extraction state.
 * The state is a singleton: all components share the same instance.
 * Timers are released when the last consumer unmounts.
 * @returns {ReturnType<typeof createExtractionState>}
 */
export function useExtractionState() {
    if (!extractionState) {
        extractionState = createExtractionState()
    }

    activeConsumersCount += 1

    onBeforeUnmount(() => {
        activeConsumersCount = Math.max(0, activeConsumersCount - 1)

        if (activeConsumersCount === 0) {
            extractionState.release()
        }
    })

    return extractionState
}
