<template>
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
		<div
			v-for="theme in themes"
			:key="theme.group"
			class="overflow-hidden rounded-lg border transition"
			:class="theme.active ? 'border-outline-gray-4 ring-1 ring-outline-gray-4' : 'border-outline-gray-1'"
		>
			<img
				v-if="theme.preview"
				:src="theme.preview"
				:alt="theme.title"
				class="aspect-video w-full border-b border-outline-gray-1 object-cover object-top"
			/>
			<div v-else class="aspect-video w-full border-b border-outline-gray-1 bg-surface-gray-2" />
			<div class="p-3">
				<div class="flex items-center justify-between gap-2">
					<span class="text-base font-medium text-ink-gray-8">{{ theme.title }}</span>
					<Badge v-if="theme.active" theme="green" variant="subtle">Active</Badge>
				</div>
				<p class="mt-1 line-clamp-2 text-sm text-ink-gray-6">{{ theme.description }}</p>
				<Button
					v-if="!theme.active"
					class="mt-3 w-full"
					:loading="applyingGroup === theme.group"
					:disabled="!!applyingGroup"
					@click="emit('apply', theme.group)"
				>
					Use this theme
				</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Badge } from 'frappe-ui'

import type { ThemeInfo } from '@/stores/onboarding'

defineProps<{ themes: ThemeInfo[]; applyingGroup?: string | null }>()

const emit = defineEmits<{ apply: [group: string] }>()
</script>
