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
    <button
        :type="type"
        :class="['btn', `btn-${variant}`, extraClass]"
        :disabled="disabled"
        :aria-label="ariaLabel"
        @click="$emit('click', $event)"
    >
        <i :class="iconClass"></i>
    </button>
</template>

<script setup>
/** Icon-only button using a Bootstrap icon class (iconClass prop). Include ariaLabel for accessibility. */
defineProps({
    iconClass: {
        type: String,
        required: true,
    },
    ariaLabel: {
        type: String,
        default: 'icon button',
    },
    variant: {
        type: String,
        default: 'outline-secondary',
    },
    type: {
        type: String,
        default: 'button',
    },
    extraClass: {
        type: String,
        default: '',
    },
    disabled: {
        type: Boolean,
        default: false,
    },
})

defineEmits(['click'])
</script>
