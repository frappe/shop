<template>
	<section class="rounded-lg border border-outline-gray-1 p-5">
		<div class="flex items-start justify-between gap-4">
			<div>
				<h2 class="text-base font-semibold text-ink-gray-9">{{ title }}</h2>
				<p v-if="description" class="mt-0.5 text-sm text-ink-gray-6">{{ description }}</p>
			</div>
			<slot name="header-action" />
		</div>
		<div class="mt-4 space-y-4">
			<slot />
		</div>
		<div v-if="$slots.footer" class="mt-5 border-t border-outline-gray-1 pt-4">
			<slot name="footer" />
		</div>
	</section>
</template>

<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>
