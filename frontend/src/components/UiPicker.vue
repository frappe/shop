<template>
	<Combobox
		v-model="value"
		:options="choices"
		:label="label"
		:description="description"
		:placeholder="placeholder"
		:error="error"
		:required="required"
		:disabled="disabled"
		:loading="loading"
		:allow-custom-value="allowCustom"
		:empty-text="search ? 'Nothing found. Try another word.' : 'Nothing matches'"
		open-on-focus
		@update:query="onQuery"
		@update:selected-option="remember"
	/>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Combobox, toast } from 'frappe-ui'

export interface PickerOption {
	label: string
	value: string
	description?: string
}

const props = withDefaults(
	defineProps<{
		modelValue?: string | null
		/** The choices, when they're known up front; searched as the person types. */
		options?: (PickerOption | string)[]
		/** Finds choices on the server instead, for long lists such as products or customers. */
		search?: (query: string) => Promise<PickerOption[]>
		/** A first choice meaning "none", e.g. "No payment fee". */
		emptyLabel?: string
		/** The chosen value's label, while the server's choices aren't loaded yet. */
		selectedLabel?: string
		/** Typed text that matches nothing is kept, e.g. a new brand. */
		allowCustom?: boolean
		label?: string
		description?: string
		placeholder?: string
		error?: string
		required?: boolean
		disabled?: boolean
	}>(),
	{ placeholder: 'Search or choose' },
)

const emit = defineEmits<{ 'update:modelValue': [string]; picked: [PickerOption] }>()

const found = ref<PickerOption[]>([])
const loading = ref(false)
const chosen = ref<PickerOption | null>(null)
let timer: ReturnType<typeof setTimeout> | null = null
let loaded = false

const value = computed({
	get: () => props.modelValue ?? (props.emptyLabel !== undefined ? '' : null),
	set: (next) => emit('update:modelValue', next ?? ''),
})

const choices = computed<PickerOption[]>(() => {
	const listed = props.search
		? found.value
		: (props.options || []).map((option) => (typeof option === 'string' ? { label: option, value: option } : option))
	const all = props.emptyLabel !== undefined ? [{ label: props.emptyLabel, value: '' }, ...listed] : [...listed]
	const current = props.modelValue
	if (current && !all.some((option) => option.value === current)) {
		all.unshift({ label: chosen.value?.value === current ? chosen.value.label : props.selectedLabel || current, value: current })
	}
	return all
})

function remember(option: PickerOption | null) {
	if (!option) return
	chosen.value = option
	emit('picked', option)
}

function onQuery(query: string) {
	if (!props.search) return
	if (timer) clearTimeout(timer)
	timer = setTimeout(() => load(query), loaded ? 250 : 0)
}

let asked = 0

async function load(query: string) {
	const mine = ++asked
	loading.value = !loaded
	try {
		const result = await props.search!(query || '')
		// an older search answering late doesn't replace a newer one
		if (mine !== asked) return
		found.value = result
		loaded = true
	} catch (error) {
		if (mine === asked) found.value = []
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not search')
	} finally {
		if (mine === asked) loading.value = false
	}
}

if (props.search) load('')
</script>
