<template>
	<header
		class="sticky top-0 z-10 -mx-6 flex items-center justify-between gap-4 border-b border-outline-gray-1 bg-surface-base px-6 py-3"
	>
		<div class="flex min-w-0 items-center gap-2">
			<router-link
				to="/products"
				aria-label="Back to products"
				class="rounded p-1 text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-8"
			>
				<LucideArrowLeft class="size-4" />
			</router-link>
			<h1 class="truncate text-lg font-semibold text-ink-gray-9">{{ title }}</h1>
		</div>
		<div class="flex shrink-0 items-center gap-3">
			<span v-if="dirty && !saving" class="text-sm text-ink-gray-5">Unsaved changes</span>
			<Button v-if="storefrontUrl" :link="storefrontUrl">
				<template #prefix><LucideExternalLink class="size-4" /></template>
				View on storefront
			</Button>
			<Button variant="solid" :disabled="!dirty" :loading="saving" @click="emit('save')">
				{{ saving ? 'Saving' : saveLabel }}
			</Button>
		</div>
	</header>
</template>

<script setup lang="ts">
import LucideArrowLeft from '~icons/lucide/arrow-left'
import LucideExternalLink from '~icons/lucide/external-link'

defineProps<{
	title: string
	saveLabel: string
	dirty: boolean
	saving: boolean
	storefrontUrl?: string
}>()

const emit = defineEmits<{ save: [] }>()
</script>
