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
    <span :class="['badge', badgeClass, extraClass]">
        <slot />
    </span>
</template>

<script setup>
/** Displays a small inline badge. Pass badgeClass to control the Bootstrap background variant. */
    defineProps({
        badgeClass:{
            type: String,
            default: 'text-bg-light'
        },
        extraClass:{
            type: String,
            default: ''
        }
    })
</script>
