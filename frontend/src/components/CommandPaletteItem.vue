<template>
	<div
		class="flex w-full min-w-0 items-center rounded px-2 py-2 text-sm text-ink-gray-8"
		:class="{ 'bg-surface-gray-2': active }">
		<component
			v-if="item.icon"
			:is="item.icon"
			:class="['mr-2.5 size-3.5 shrink-0', active ? 'text-ink-gray-7' : 'text-ink-gray-5']" />
		<span class="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap">
			{{ item.title }}
		</span>
		<span v-if="item.description && showDescription" class="ml-3 shrink-0 text-xs text-ink-gray-4">
			{{ item.description }}
		</span>
	</div>
</template>

<script setup lang="ts">
withDefaults(
	defineProps<{
		item: {
			name: string
			title: string
			description?: string
			icon?: object
			[key: string]: unknown
		}
		active?: boolean
		showDescription?: boolean
	}>(),
	{ showDescription: false },
)
</script>
