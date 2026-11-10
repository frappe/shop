<template>
	<div>
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="min-w-0">
				<h2 v-if="title" class="text-base font-medium text-ink-gray-8">{{ title }}</h2>
				<p v-if="description" class="mt-0.5 text-p-sm text-ink-gray-5">{{ description }}</p>
			</div>
			<Button @click="openEditor()">
				<template #prefix><LucidePlus class="size-3.5" /></template>
				{{ item ? 'Add quantity break' : 'Add rate' }}
			</Button>
		</div>

		<p v-if="rates.error" class="mt-3 text-p-sm text-ink-red-8">
			{{ errorMessage(rates.error, 'Could not load the rates') }}
			<button type="button" class="underline" @click="rates.reload()">Try again</button>
		</p>
		<p v-else-if="rates.data && !rows.length" class="mt-3 text-p-sm text-ink-gray-5">{{ emptyText }}</p>

		<div v-if="rows.length" class="mt-3 divide-y divide-outline-gray-1 rounded border border-outline-gray-1">
			<div v-for="row in rows" :key="row.target_type + row.target" class="flex flex-wrap items-start gap-3 px-3 py-2.5">
				<div class="min-w-0 flex-1">
					<div v-if="!item" class="flex items-center gap-2">
						<span class="text-base text-ink-gray-8">{{ row.label }}</span>
						<Badge size="sm" variant="subtle" theme="gray">{{ row.target_type === 'Product' ? 'Product' : 'Item Group' }}</Badge>
					</div>
					<div class="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-sm text-ink-gray-6">
						<span v-for="tier in row.tiers" :key="tier.name">
							<span class="text-ink-gray-5">{{ tierStart(tier) }}:</span> {{ tier.label }}
						</span>
					</div>
				</div>
				<div class="flex gap-1">
					<Button variant="ghost" @click="openEditor(row)">Edit</Button>
					<Button variant="ghost" theme="red" :loading="removing === row.target" @click="confirmRemove(row)">
						Remove
					</Button>
				</div>
			</div>
		</div>

		<p v-if="rates.data?.set_in_desk" class="mt-3 text-p-sm text-ink-gray-5">
			{{ rates.data.set_in_desk }} more {{ rates.data.set_in_desk === 1 ? 'rule is' : 'rules are' }} set up in
			Desk (Pricing Rule) in ways this page doesn't show.
		</p>

		<Dialog
			v-model="editing"
			:options="{
				title: form.existing ? `Rates for ${form.label}` : item ? 'Quantity breaks' : 'Add rate',
				size: 'xl',
				actions: [{ label: 'Save', variant: 'solid', loading: saving, onClick: save }],
			}"
		>
			<div class="space-y-4">
				<template v-if="!item && !form.existing">
					<TabButtons
						v-model="form.target_type"
						:options="[
							{ label: 'Item Group', value: 'Item Group' },
							{ label: 'Product', value: 'Product' },
						]"
					/>
					<UiPicker
						v-if="form.target_type === 'Item Group'"
						v-model="form.target"
						label="Item Group"
						description="The rate covers every product in this Item Group and the groups inside it."
						:options="groupOptions"
						placeholder="Choose an Item Group"
					/>
					<UiPicker
						v-else
						v-model="form.target"
						label="Product"
						description="Search by product name or item code."
						:search="findProducts"
						:selected-label="form.label"
						placeholder="Choose a product"
						@picked="(option) => (form.label = option.label)"
					/>
				</template>

				<div>
					<div class="grid grid-cols-[6rem_9rem_1fr_2rem] items-end gap-2 text-sm text-ink-gray-5">
						<span>From quantity</span>
						<span>Rate</span>
						<span>{{ currencyHint }}</span>
						<span />
					</div>
					<div
						v-for="(tier, index) in form.tiers"
						:key="index"
						class="mt-2 grid grid-cols-[6rem_9rem_1fr_2rem] items-center gap-2"
					>
						<FormControl v-model.number="tier.from_qty" type="number" :min="1" aria-label="From quantity" />
						<FormControl
							v-model="tier.kind"
							type="select"
							aria-label="Rate"
							:options="[
								{ label: '% off', value: 'discount' },
								{ label: 'Fixed price', value: 'price' },
							]"
						/>
						<FormControl
							v-model.number="tier.value"
							type="number"
							:min="0"
							:aria-label="tier.kind === 'price' ? 'Price' : 'Percent off'"
						/>
						<Button
							variant="ghost"
							:disabled="form.tiers.length === 1"
							:aria-label="`Remove the rate from ${tier.from_qty}`"
							@click="form.tiers.splice(index, 1)"
						>
							<template #icon><LucideX class="size-3.5" /></template>
						</Button>
					</div>
					<Button class="mt-2" variant="ghost" @click="addTier">
						<template #prefix><LucidePlus class="size-3.5" /></template>
						Add quantity break
					</Button>
				</div>
				<p class="text-p-sm text-ink-gray-5">
					A rate from quantity 1 applies to any quantity; each quantity break applies from its quantity up to
					the next one. {{ scopeNote }}
				</p>
			</div>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { Badge, Button, Dialog, FormControl, TabButtons, call, createResource, dialog, toast } from 'frappe-ui'

import UiPicker from '@/components/UiPicker.vue'
import LucidePlus from '~icons/lucide/plus'
import LucideX from '~icons/lucide/x'

interface Tier {
	name?: string
	kind: 'discount' | 'price'
	value: number
	label?: string
	from_qty: number
}

interface RateRow {
	target_type: 'Item Group' | 'Product'
	target: string
	label: string
	tiers: Tier[]
}

const props = defineProps<{
	scope: 'trade' | 'customer' | 'everyone'
	customer?: string
	item?: string
	itemLabel?: string
	title?: string
	description?: string
}>()

const rates = createResource({
	url: 'shop.api.pricing.get_rates',
	makeParams: () => ({ scope: props.scope, customer: props.customer, item: props.item }),
	auto: true,
})
const rows = computed<RateRow[]>(() => rates.data?.rates || [])
const groupOptions = computed(() =>
	(rates.data?.item_groups || []).map((group: { name: string; depth: number }) => ({
		label: `${'  '.repeat(Math.max(group.depth - 1, 0))}${group.name}`,
		value: group.name,
	})),
)
const currencyHint = computed(() => `% or price in ${rates.data?.currency || 'the store currency'}`)
const emptyText = computed(() =>
	props.item
		? 'No quantity breaks for this product.'
		: props.scope === 'customer'
			? 'No rates of their own.'
			: 'No trade rates yet.',
)
const scopeNote = computed(
	() =>
		({
			trade: 'These are for every trade account; a customer can be given their own.',
			customer: 'Their own rate replaces the trade rate for the same Item Group or product.',
			everyone: 'These are for every customer; trade rates replace them for trade accounts.',
		})[props.scope],
)

function tierStart(tier: Tier) {
	return tier.from_qty > 1 ? `From ${tier.from_qty}` : 'Any quantity'
}

function errorMessage(error: unknown, fallback: string) {
	const messages = (error as { messages?: string[] } | null)?.messages
	return messages?.[0] || fallback
}

const editing = ref(false)
const saving = ref(false)
const removing = ref('')
const form = reactive({
	existing: false,
	target_type: 'Item Group' as 'Item Group' | 'Product',
	target: '',
	label: '',
	tiers: [] as Tier[],
})

function openEditor(row?: RateRow) {
	// a product's breaks are one set: a new break is added to those it has
	const own = !row && props.item ? rows.value.find((other) => other.target === props.item) : undefined
	if (own) {
		openEditor(own)
		addTier()
		return
	}
	Object.assign(form, {
		existing: !!row,
		target_type: row?.target_type || (props.item ? 'Product' : 'Item Group'),
		target: row?.target || props.item || '',
		label: row?.label || props.itemLabel || '',
		tiers: row
			? row.tiers.map((tier) => ({ kind: tier.kind, value: tier.value, from_qty: Math.max(tier.from_qty, 1) }))
			: [{ kind: 'discount', value: 0, from_qty: props.item ? 10 : 1 }],
	})
	editing.value = true
}

function addTier() {
	const last = form.tiers[form.tiers.length - 1]
	form.tiers.push({ kind: last?.kind || 'discount', value: 0, from_qty: Math.max((last?.from_qty || 1) * 2, 10) })
}

// a new rate for something that has rates already joins them rather than replacing them
function withExisting(tiers: Tier[]) {
	const row = rows.value.find((other) => other.target_type === form.target_type && other.target === form.target)
	if (!row) return tiers
	const kept = row.tiers
		.map((tier) => ({ kind: tier.kind, value: tier.value, from_qty: Math.max(tier.from_qty, 1) }))
		.filter((tier) => !tiers.some((added) => added.from_qty === tier.from_qty))
	return [...kept, ...tiers].sort((a, b) => a.from_qty - b.from_qty)
}

async function save() {
	if (!form.target) {
		toast.error(form.target_type === 'Product' ? 'Choose a product' : 'Choose an Item Group')
		return
	}
	saving.value = true
	try {
		const result = await call('shop.api.pricing.save_rates', {
			scope: props.scope,
			customer: props.customer,
			target_type: form.target_type,
			target: form.target,
			tiers: form.existing ? form.tiers : withExisting(form.tiers),
		})
		// the answer lists every rate of the scope, not only this product's
		if (props.item) rates.reload()
		else rates.data = result
		editing.value = false
		toast.success('Rates saved')
	} catch (error) {
		toast.error(errorMessage(error, 'Could not save the rates'))
	} finally {
		saving.value = false
	}
}

function confirmRemove(row: RateRow) {
	dialog.confirm({
		title: 'Remove rates',
		message: `Remove the rates for ${row.label}?`,
		theme: 'red',
		confirmLabel: 'Remove',
		onConfirm: async () => {
			removing.value = row.target
			try {
				await call('shop.api.pricing.remove_rates', {
					scope: props.scope,
					customer: props.customer,
					target_type: row.target_type,
					target: row.target,
				})
				rates.reload()
				toast.success('Rates removed')
			} catch (error) {
				toast.error(errorMessage(error, 'Could not remove the rates'))
			} finally {
				removing.value = ''
			}
		},
	})
}

async function findProducts(text: string) {
	const result = (await call('shop.api.products.get_products', { search: text, limit: 20 })) as {
		products: { item: string; product_name: string }[]
	}
	return result.products
		.filter((product) => product.item)
		.map((product) => ({ label: product.product_name, value: product.item, description: product.item }))
}
</script>
