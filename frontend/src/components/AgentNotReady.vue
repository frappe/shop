<template>
	<div class="flex h-full items-center justify-center px-6 py-12">
		<div class="w-full max-w-md rounded-xl border border-outline-gray-2 bg-surface-white p-6 text-center">
			<div class="mx-auto flex size-11 items-center justify-center rounded-full bg-surface-gray-2">
				<LucideSparkles class="size-5 text-ink-gray-7" />
			</div>
			<h1 class="mt-4 text-lg font-semibold text-ink-gray-9">
				Connect a model to use the assistant
			</h1>
			<p class="mt-2 text-base leading-6 text-ink-gray-6">{{ explanation }}</p>
			<Button class="mt-5" variant="solid" link="/app/flow-model/new">
				<template #suffix><LucideExternalLink class="size-4" /></template>
				Add a model
			</Button>
			<p class="mt-4 text-sm leading-5 text-ink-gray-5">
				Once a model is connected, the assistant can manage your catalogue, orders, stock,
				discounts and settings.
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from 'frappe-ui'

import LucideExternalLink from '~icons/lucide/external-link'
import LucideSparkles from '~icons/lucide/sparkles'

const props = defineProps<{ reason?: string }>()

const explanation = computed(() =>
	props.reason === 'not_installed'
		? 'Flow is not installed on this site, so the assistant has nothing to run on. Install it, then connect a model.'
		: 'No model is configured yet. Add one with your provider key to switch the assistant on.',
)
</script>
