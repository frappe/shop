<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<UiPageHeader
			title="Specifications"
			subtitle="The details products are described by, such as Capacity or Interface. They show as a table on each product page, and those set as filters let shoppers narrow a collection by them."
		>
			<template #actions>
				<Button variant="solid" @click="openEditor()">
					<template #prefix><LucidePlus class="size-4" /></template>
					New specification
				</Button>
			</template>
		</UiPageHeader>

		<UiDataTable class="mt-6" :columns="columns" :rows="rows" row-key="name" :loading="!specifications.fetched">
			<template #cell-name="{ row }">
				<span class="font-medium text-ink-gray-8">{{ row.name }}</span>
			</template>
			<template #cell-use_as_filter="{ row }">{{ row.use_as_filter ? 'Yes' : 'No' }}</template>
			<template #cell-actions="{ row }">
				<div class="flex justify-end gap-1">
					<Button variant="ghost" @click="openEditor(row as Specification)">Edit</Button>
					<Button
						variant="ghost"
						theme="red"
						:disabled="row.products > 0"
						:title="row.products ? 'Take it off its products first' : ''"
						@click="confirmDelete(row as Specification)"
					>
						Remove
					</Button>
				</div>
			</template>
			<template #empty>
				<UiEmptyState
					:icon="LucideListChecks"
					title="No specifications yet"
					message="Add them here, or type one in a product's Specifications."
				/>
			</template>
		</UiDataTable>

		<Dialog
			v-model="editing"
			:options="{
				title: form.name ? `Edit ${form.name}` : 'New specification',
				actions: [{ label: 'Save', variant: 'solid', loading: saving, onClick: save }],
			}"
		>
			<div class="space-y-4">
				<FormControl v-model="form.specification_name" label="Name" placeholder="Capacity" required />
				<FormControl
					v-model="form.unit"
					label="Unit"
					placeholder="GB"
					description="Shown after each value. Leave empty when the values say it."
				/>
				<Switch
					v-model="form.use_as_filter"
					label="Use as a filter"
					description="Shoppers can narrow a collection's products by it."
					class="!w-auto"
				/>
				<FormControl
					v-model.number="form.ranking"
					type="number"
					label="Ranking"
					description="Filters with a higher ranking are listed first."
					class="w-40"
				/>
			</div>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { Button, Dialog, FormControl, Switch, call, createResource, dialog, toast } from 'frappe-ui'

import LucideListChecks from '~icons/lucide/list-checks'
import LucidePlus from '~icons/lucide/plus'

import UiDataTable from '@/components/UiDataTable.vue'
import UiEmptyState from '@/components/UiEmptyState.vue'
import UiPageHeader from '@/components/UiPageHeader.vue'

interface Specification {
	name: string
	unit: string | null
	use_as_filter: number
	ranking: number
	products: number
}

const specifications = createResource({ url: 'shop.api.products.get_specifications', auto: true })
const rows = computed<Specification[]>(() => specifications.data || [])

const columns = [
	{ key: 'name', label: 'Specification' },
	{ key: 'unit', label: 'Unit' },
	{ key: 'use_as_filter', label: 'Filter' },
	{ key: 'ranking', label: 'Ranking', align: 'right' as const },
	{ key: 'products', label: 'Products', align: 'right' as const },
	{ key: 'actions', label: '', align: 'right' as const },
]

function errorMessage(error: unknown, fallback: string) {
	const messages = (error as { messages?: string[] } | null)?.messages
	return messages?.[0] || fallback
}

const editing = ref(false)
const saving = ref(false)
const form = reactive({ name: '', specification_name: '', unit: '', use_as_filter: true, ranking: 0 })

function openEditor(row?: Specification) {
	Object.assign(form, {
		name: row?.name || '',
		specification_name: row?.name || '',
		unit: row?.unit || '',
		use_as_filter: row ? !!row.use_as_filter : true,
		ranking: row?.ranking || 0,
	})
	editing.value = true
}

async function save() {
	saving.value = true
	try {
		specifications.data = await call('shop.api.products.save_specification', {
			name: form.name || undefined,
			specification_name: form.specification_name,
			unit: form.unit,
			use_as_filter: form.use_as_filter ? 1 : 0,
			ranking: form.ranking || 0,
		})
		editing.value = false
		toast.success('Specification saved')
	} catch (error) {
		toast.error(errorMessage(error, 'Could not save the specification'))
	} finally {
		saving.value = false
	}
}

function confirmDelete(row: Specification) {
	dialog.confirm({
		title: 'Remove specification',
		message: `Remove ${row.name}?`,
		theme: 'red',
		confirmLabel: 'Remove',
		onConfirm: async () => {
			try {
				specifications.data = await call('shop.api.products.delete_specification', { name: row.name })
				toast.success('Specification removed')
			} catch (error) {
				toast.error(errorMessage(error, 'Could not remove the specification'))
			}
		},
	})
}
</script>
