<template>
	<div
		class="flex cursor-pointer flex-col gap-2 rounded-lg border border-outline-gray-1 p-4 transition hover:bg-surface-gray-1"
		@click="emit('start')"
	>
		<div class="flex items-start justify-between gap-3">
			<div class="text-base font-medium text-ink-gray-9">{{ guide.title }}</div>
			<Button class="shrink-0" :loading="preparing" @click.stop="emit('start')">Start</Button>
		</div>
		<p class="text-sm text-ink-gray-6">{{ guide.tagline }}</p>
		<div class="mt-auto flex flex-wrap gap-1.5 pt-1">
			<Badge theme="gray">~{{ guide.minutes }} min</Badge>
			<Badge theme="gray">{{ guide.viewport }}</Badge>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Badge } from 'frappe-ui'

import type { PersonaGuide } from '@/components/WalkthroughGuide.vue'

defineProps<{ guide: PersonaGuide; preparing: boolean }>()
const emit = defineEmits<{ start: [] }>()
</script>
