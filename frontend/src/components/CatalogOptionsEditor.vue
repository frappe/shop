<template>
	<div class="space-y-3">
		<div v-for="(option, index) in model" :key="index" class="rounded border border-outline-gray-1 p-3">
			<div class="flex items-start gap-4">
				<div class="w-44 shrink-0">
					<FormControl
						:model-value="option.attribute"
						label="Option"
						placeholder="Size"
						@update:model-value="(value: string) => setAttribute(index, value)"
					/>
					<div v-if="attributeSuggestions(index).length" class="mt-1.5 flex flex-wrap gap-1">
						<button
							v-for="name in attributeSuggestions(index)"
							:key="name"
							type="button"
							class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-sm text-ink-gray-6 hover:bg-surface-gray-3 hover:text-ink-gray-8"
							@click="setAttribute(index, name)"
						>
							{{ name }}
						</button>
					</div>
				</div>

				<div class="min-w-0 flex-1">
					<label class="block text-base text-ink-gray-5">Values</label>
					<div
						class="mt-1.5 flex min-h-7 flex-wrap items-center gap-1.5 rounded border border-outline-gray-2 bg-surface-white px-1.5 py-1"
					>
						<span
							v-for="value in option.values"
							:key="value"
							class="flex items-center gap-1 rounded bg-surface-gray-2 py-0.5 pl-2 pr-1 text-sm text-ink-gray-8"
						>
							{{ value }}
							<button
								type="button"
								:aria-label="`Remove ${value}`"
								class="text-ink-gray-5 hover:text-ink-gray-8"
								@click="removeValue(index, value)"
							>
								<LucideX class="size-3" />
							</button>
						</span>
						<input
							v-model="drafts[index]"
							type="text"
							:placeholder="option.values.length ? 'Add value' : 'Type a value and press Enter'"
							class="min-w-32 flex-1 border-0 bg-transparent p-0 text-base text-ink-gray-8 placeholder-ink-gray-4 focus:outline-none focus:ring-0"
							@keydown.enter.prevent="commitDraft(index)"
							@keydown.backspace="onBackspace(index, option)"
							@blur="commitDraft(index)"
						/>
					</div>
					<div v-if="valueSuggestions(option).length" class="mt-1.5 flex flex-wrap gap-1">
						<button
							v-for="value in valueSuggestions(option)"
							:key="value"
							type="button"
							class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-sm text-ink-gray-6 hover:bg-surface-gray-3 hover:text-ink-gray-8"
							@click="addValue(index, value)"
						>
							{{ value }}
						</button>
					</div>
				</div>

				<Button variant="ghost" theme="red" class="mt-6 shrink-0" @click="removeOption(index)">
					<template #icon><LucideTrash2 class="size-4" /></template>
				</Button>
			</div>
		</div>

		<div class="flex items-center justify-between gap-4">
			<Button @click="addOption">
				<template #prefix><LucidePlus class="size-4" /></template>
				Add option
			</Button>
			<p class="text-sm" :class="error ? 'text-ink-red-8' : 'text-ink-gray-5'">
				{{ error || combinationHint }}
			</p>
		</div>
	</div>
</template>

<script lang="ts">
export interface ProductOption {
	attribute: string
	values: string[]
}

export function combinationCount(options: ProductOption[]): number {
	if (!options.length) return 0
	return options.reduce((total, option) => total * option.values.length, 1)
}

export function optionsError(options: ProductOption[]): string {
	if (!options.length) return 'Add at least one option'
	const seen = new Set<string>()
	for (const option of options) {
		const name = option.attribute.trim()
		if (!name) return 'Give every option a name'
		if (seen.has(name.toLowerCase())) return `${name} is added twice`
		seen.add(name.toLowerCase())
		if (!option.values.length) return `Add at least one value for ${name}`
	}
	return ''
}
</script>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, FormControl, call, toast } from 'frappe-ui'

import LucidePlus from '~icons/lucide/plus'
import LucideTrash2 from '~icons/lucide/trash-2'
import LucideX from '~icons/lucide/x'

const model = defineModel<ProductOption[]>({ required: true })

const known = ref<ProductOption[]>([])
const drafts = reactive<Record<number, string>>({})

const error = computed(() => optionsError(model.value))

const combinationHint = computed(() => {
	const count = combinationCount(model.value)
	return `This will create ${count} ${count === 1 ? 'combination' : 'combinations'}`
})

onMounted(loadAttributes)

async function loadAttributes() {
	try {
		known.value = await call('shop.api.variants.get_attributes')
	} catch (error) {
		toast.error('Could not load saved options')
	}
}

function attributeSuggestions(index: number) {
	const used = model.value
		.filter((_, i) => i !== index)
		.map((option) => option.attribute.trim().toLowerCase())
	const current = model.value[index].attribute.trim().toLowerCase()
	return known.value
		.map((option) => option.attribute)
		.filter((name) => !used.includes(name.toLowerCase()) && name.toLowerCase() !== current)
}

function valueSuggestions(option: ProductOption) {
	const match = known.value.find(
		(entry) => entry.attribute.toLowerCase() === option.attribute.trim().toLowerCase(),
	)
	const chosen = option.values.map((value) => value.toLowerCase())
	return (match?.values || []).filter((value) => !chosen.includes(value.toLowerCase()))
}

function update(index: number, changes: Partial<ProductOption>) {
	model.value = model.value.map((option, i) => (i === index ? { ...option, ...changes } : option))
}

function addOption() {
	model.value = [...model.value, { attribute: '', values: [] }]
}

function removeOption(index: number) {
	model.value = model.value.filter((_, i) => i !== index)
	delete drafts[index]
}

function setAttribute(index: number, name: string) {
	update(index, { attribute: name })
}

function addValue(index: number, value: string) {
	const clean = value.trim()
	const option = model.value[index]
	if (!clean || option.values.some((existing) => existing.toLowerCase() === clean.toLowerCase())) return
	update(index, { values: [...option.values, clean] })
}

function removeValue(index: number, value: string) {
	update(index, { values: model.value[index].values.filter((existing) => existing !== value) })
}

function commitDraft(index: number) {
	addValue(index, drafts[index] || '')
	drafts[index] = ''
}

function onBackspace(index: number, option: ProductOption) {
	if (drafts[index] || !option.values.length) return
	removeValue(index, option.values[option.values.length - 1])
}
</script>
