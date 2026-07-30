<template>
	<div class="flex flex-wrap items-center gap-2">
		<div v-if="searchPlaceholder" class="w-56">
			<FormControl v-model="search" type="text" :placeholder="searchPlaceholder">
				<template #prefix>
					<LucideSearch class="size-4 text-ink-gray-5" />
				</template>
			</FormControl>
		</div>
		<slot />
		<div class="ml-auto text-sm text-ink-gray-5">
			<slot name="trailing" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { FormControl, debounce } from 'frappe-ui'

import LucideSearch from '~icons/lucide/search'

const props = defineProps<{
	modelValue?: string
	searchPlaceholder?: string
}>()

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const search = ref(props.modelValue || '')
watch(
	search,
	debounce((value: string) => emit('update:modelValue', value), 300),
)
</script>
