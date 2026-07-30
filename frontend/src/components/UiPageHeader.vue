<template>
	<div>
		<router-link
			v-if="backTo"
			:to="backTo"
			class="mb-2 inline-flex items-center gap-1 text-sm text-ink-gray-5 hover:text-ink-gray-8"
		>
			<LucideArrowLeft class="size-3.5" />
			{{ backLabel }}
		</router-link>
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div class="flex items-center gap-3">
				<h1 class="text-xl font-semibold text-ink-gray-9">{{ title }}</h1>
				<slot name="badges" />
			</div>
			<div class="flex items-center gap-2">
				<slot name="actions" />
			</div>
		</div>
		<p v-if="subtitle" class="mt-1 text-base text-ink-gray-6">{{ subtitle }}</p>
	</div>
</template>

<script setup lang="ts">
import LucideArrowLeft from '~icons/lucide/arrow-left'

defineProps<{
	title: string
	subtitle?: string
	backTo?: string
	backLabel?: string
}>()
</script>
