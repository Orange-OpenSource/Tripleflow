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
        @click="$emit('click', $event)"
    >
        <slot />
    </button>
</template>

<script setup>
/** Styled Bootstrap button with slot content. Set variant to control the color, and disabled to prevent interaction. */
defineProps({
    variant: {
        type: String,
        default: 'primary'
    },
    type: {
        type: String,
        default: 'button'
    },
    extraClass: {
        type: String,
        default: ''
    },
    disabled: {
        type: Boolean,
        default: false
    }
})

defineEmits(['click'])
</script>
