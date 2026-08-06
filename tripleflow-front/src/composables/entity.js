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
 * Shared helpers for entity values (labels and QID/PID identifiers).
 */

/** Placeholder shown in the UI when an entity value (label or QID/PID) is missing. */
export const ENTITY_PLACEHOLDER = '-'

/**
 * Returns true when a value represents an empty or null-like entity payload.
 * Covers explicit null/undefined as well as sentinel strings ("none", "n/a", "-", …).
 * @param {*} value
 * @returns {boolean}
 */
export function isNullLikeEntityValue(value) {
    if (value === null || value === undefined) {
        return true
    }

    if (typeof value !== 'string') {
        return false
    }

    const normalized = value.trim().toLowerCase()
    return normalized === ''
        || normalized === 'none'
        || normalized === 'null'
        || normalized === 'n/a'
        || normalized === 'na'
        || normalized === '-'
        || normalized === 'undefined'
}
