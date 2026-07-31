<template>
	<div class="flex flex-col items-center gap-2 px-4 py-12 text-center">
		<component :is="icon" v-if="icon" class="size-6 text-ink-gray-4" />
		<div class="text-base font-medium text-ink-gray-7">{{ title }}</div>
		<div v-if="message" class="max-w-sm text-p-sm text-ink-gray-5">{{ message }}</div>
		<div class="mt-2">
			<slot name="action" />
		</div>
	</div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
	title: string
	message?: string
	icon?: Component
}>()
</script>
