<template>
	<MultiSelect
		v-model="values"
		:options="choices"
		:label="label"
		:description="description"
		:placeholder="placeholder"
		empty-text="Nothing listed yet. Type a name to add it."
	>
		<template #footer="{ query }">
			<div class="flex items-center justify-between gap-2 px-1 py-1">
				<Button
					v-if="query.trim() && !listed(query)"
					variant="ghost"
					size="sm"
					:label="`Add “${query.trim()}”`"
					@click="add(query)"
				/>
				<span v-else class="px-1 text-p-xs text-ink-gray-5">Type to search or add a name</span>
				<Button v-if="values.length" variant="ghost" size="sm" label="Clear" @click="values = []" />
			</div>
		</template>
	</MultiSelect>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, MultiSelect } from 'frappe-ui'

const props = withDefaults(
	defineProps<{
		modelValue?: string[]
		/** Names to choose from; ones typed in are added to them. */
		options?: string[]
		label?: string
		description?: string
		placeholder?: string
	}>(),
	{ modelValue: () => [], options: () => [], placeholder: 'Choose' },
)

const emit = defineEmits<{ 'update:modelValue': [string[]] }>()

const added = ref<string[]>([])

const values = computed({
	get: () => props.modelValue,
	set: (next: string[]) => emit('update:modelValue', next),
})

const choices = computed(() =>
	[...new Set([...props.options, ...added.value, ...props.modelValue])].map((name) => ({ label: name, value: name })),
)

function listed(query: string) {
	return choices.value.some((option) => option.value.toLowerCase() === query.trim().toLowerCase())
}

function add(query: string) {
	const name = query.trim()
	added.value.push(name)
	values.value = [...values.value, name]
}
</script>
