/*  
Software Name : Tripleflow
SPDX-FileCopyrightText: Copyright (c) Orange SA
SPDX-License-Identifier: MIT
 
This software is distributed under the MIT License,
see the "LICENSE" file for more details or https://spdx.org/licenses/MIT.html
 
Authors: Sonia Hadjab, Antoine Py, Yoan Chabot
Software description: Tripleflow is a tool that enables semi-supervised data feeding of knowledge graphs from unstructured documents.  

*/
import * as pdfjsLib from 'pdfjs-dist'
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

import { parseFile } from './api'
import {
    FILE_READ_ERROR,
    SUPPORTED_FILE_EXTENSIONS,
} from './constants'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker

/** Returns true if the file is a plain text file (.txt or text/plain MIME type). */
export function isTxtFile(file) {
    if (!file) {
        return false
    }

    return file.type === 'text/plain' || file.name.toLowerCase().endsWith('.txt')
}

/** Returns true if the file is a PDF (.pdf or application/pdf MIME type). */
export function isPdfFile(file) {
    if (!file) {
        return false
    }

    return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}

/**
 * Returns true if the file is one the pipeline accepts (.txt or .pdf).
 * Independent of the parsing mode: both read the same formats.
 * @param {File} file
 */
export function isSupportedFile(file) {
    if (!file) {
        return false
    }

    const name = file.name.toLowerCase()
    return SUPPORTED_FILE_EXTENSIONS.some((extension) => name.endsWith(extension))
}

/** Returns true if two File objects refer to the same file (same name, size, and last-modified timestamp). */
export function isSameFile(firstFile, secondFile) {
    return firstFile.name === secondFile.name
        && firstFile.size === secondFile.size
        && firstFile.lastModified === secondFile.lastModified
}

/** Joins the names of an array of File objects into a comma-separated display string. */
export function buildSelectedFileName(files) {
    return files.map((file) => file.name).join(', ')
}

/** Builds a stable string key for a File object, used to detect duplicate uploads. */
export function buildFileKey(file) {
    return `${file.name}-${file.size}-${file.lastModified}`
}

/**
 * Joins content from multiple files into a single string.
 * If there is only one file, returns its content directly.
 * Otherwise, each section is prefixed with a file name header.
 * @param {{ name: string, content: string }[]} parts
 * @returns {string}
 */
function formatCombinedFileText(parts) {
    if (parts.length === 1) {
        return parts[0].content.trim()
    }

    return parts
        .map(({ name, content }) => `--- ${name} ---\n${content}`.trim())
        .join('\n\n')
        .trim()
}

/** Separates consecutive pages in the text built from a PDF. */
const PAGE_SEPARATOR = '\n\n'

/**
 * Extracts plain text from a PDF file using pdf.js, in the browser.
 * Pages are separated by double newlines; empty pages contribute no text but
 * still claim an offset, so the pages after them keep their real numbers.
 * @param {File} file
 * @returns {Promise<{ text: string, pageOffsets: number[] }>}
 */
async function extractTextFromPdf(file) {
    const arrayBuffer = await file.arrayBuffer()
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
    const pagesText = []
    const pageOffsets = []
    let cursor = 0

    for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
        const page = await pdf.getPage(pageNumber)
        const content = await page.getTextContent()
        const pageText = content.items
            .map((item) => ('str' in item ? item.str : ''))
            .join(' ')
            .replace(/\s+/g, ' ')
            .trim()

        pageOffsets.push(cursor)

        if (pageText) {
            pagesText.push(pageText)
            cursor += pageText.length + PAGE_SEPARATOR.length
        }
    }

    return { text: pagesText.join(PAGE_SEPARATOR), pageOffsets }
}

/**
 * Reads a text file as a UTF-8 string using the FileReader API.
 * @param {File} file
 * @returns {Promise<string>}
 */
function readTextFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader()

        reader.onload = (event) => {
            resolve(event.target?.result || '')
        }

        reader.onerror = () => {
            reject(new Error(FILE_READ_ERROR))
        }

        reader.readAsText(file, 'utf-8')
    })
}

/**
 * Reads a File object and returns its text content, along with the offset at
 * which each page starts (empty for formats that have no pages).
 * Advanced mode delegates to the backend /parse endpoint (Docling): richer
 * Markdown output and many more formats, at the cost of a round-trip.
 * Basic mode (the default) parses in the browser with pdf.js / FileReader.
 * @param {File} file
 * @param {boolean} advancedParsing
 * @returns {Promise<{ text: string, pageOffsets: number[] }>}
 */
export async function readFileText(file, advancedParsing = false) {
    if (advancedParsing) {
        return parseFile(file)
    }

    if (isPdfFile(file)) {
        return extractTextFromPdf(file)
    }

    return { text: await readTextFile(file), pageOffsets: [] }
}

/**
 * Builds a combined text string from an array of already-read file entries ({ name, text }).
 * @param {{ name: string, text: string }[]} entries
 * @returns {string}
 */
export function buildTextFromEntries(entries) {
    return formatCombinedFileText(
        entries.map((entry) => ({
            name: entry.name,
            content: entry.text,
        }))
    )
}

/**
 * Reads all files in the array and combines their text content into a single string.
 * @param {File[]} files
 * @param {boolean} advancedParsing
 * @returns {Promise<string>}
 */
export async function buildTextFromFiles(files, advancedParsing = false) {
    const extractedParts = []

    for (const file of files) {
        const { text } = await readFileText(file, advancedParsing)
        extractedParts.push({ name: file.name, content: text })
    }

    return formatCombinedFileText(extractedParts)
}
