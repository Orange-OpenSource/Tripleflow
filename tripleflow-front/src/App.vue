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
    <div id="app">
        <HeaderBar :currentPage="currentPage" @navigate="currentPage = $event" />
        <HomePage v-if="currentPage === 'home'" @navigate="currentPage = $event" />
        <ValidationPage v-else-if="currentPage === 'validation'" />
        <GraphPage v-else-if="currentPage === 'graph'" />
        <ExtractorsPage v-else-if="currentPage === 'extractors'" />
        <TargetsPage v-else-if="currentPage === 'targets'" />
        <FooterBar />
    </div>
</template>


<script setup>
import { provide, ref } from 'vue'
import HeaderBar from './components/layout/HeaderBar.vue'
import FooterBar from './components/layout/FooterBar.vue'
import HomePage from './pages/HomePage.vue'
import ValidationPage from './pages/ValidationPage.vue'
import GraphPage from './pages/GraphPage.vue'
import ExtractorsPage from './pages/ExtractorsPage.vue'
import TargetsPage from './pages/TargetsPage.vue'

const currentPage = ref('home')
const reviewerName = ref('')
provide('reviewerName', reviewerName)
</script>


<style>
#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
</style>
