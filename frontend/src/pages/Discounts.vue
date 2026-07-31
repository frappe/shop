<template>
	<div class="mx-auto max-w-4xl px-6 py-8">
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-xl font-semibold text-ink-gray-9">Discounts</h1>
				<p class="mt-1 text-p-sm text-ink-gray-6">Shoppers enter these codes at checkout.</p>
			</div>
			<Button variant="solid" @click="openNew">
				<template #prefix><LucidePlus class="size-4" /></template>
				New coupon
			</Button>
		</div>

		<CatalogListState
			:loading="coupons.loading && !coupons.data"
			:error="coupons.error"
			:empty="!rows.length"
			empty-title="No coupons yet"
			empty-subtitle="Create a coupon code to offer discounts at checkout."
			@retry="coupons.reload()"
		>
			<template #action>
				<Button variant="solid" @click="openNew">New coupon</Button>
			</template>
		</CatalogListState>

		<div v-if="rows.length && !coupons.error" class="mt-6 overflow-hidden rounded-lg border border-outline-gray-1">
			<table class="w-full text-base">
				<thead>
					<tr class="border-b border-outline-gray-1 text-left text-sm text-ink-gray-5">
						<th class="px-3 py-2 font-normal">Code</th>
						<th class="px-3 py-2 font-normal">Discount</th>
						<th class="px-3 py-2 text-right font-normal">Used</th>
						<th class="px-3 py-2 font-normal">Validity</th>
						<th class="px-3 py-2 text-right font-normal">Enabled</th>
						<th class="w-10 px-1 py-2"></th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="row in rows"
						:key="row.name"
						class="cursor-pointer border-b border-outline-gray-1 last:border-b-0 hover:bg-surface-gray-1"
						@click="openEdit(row)"
					>
						<td class="px-3 py-2">
							<span class="rounded bg-surface-gray-2 px-1.5 py-0.5 font-mono text-sm text-ink-gray-8">
								{{ row.coupon_code }}
							</span>
						</td>
						<td class="px-3 py-2 text-ink-gray-7">
							{{ row.value_label }}
							<span v-if="row.min_amt" class="text-sm text-ink-gray-5">over {{ row.min_amt }}</span>
						</td>
						<td class="px-3 py-2 text-right text-ink-gray-7">
							{{ row.used }}<span v-if="row.maximum_use" class="text-ink-gray-5"> of {{ row.maximum_use }}</span>
						</td>
						<td class="px-3 py-2 text-sm text-ink-gray-6">{{ validity(row) }}</td>
						<td class="px-3 py-2 text-right" @click.stop>
							<Switch
								:model-value="!!row.enabled"
								@update:model-value="(value: boolean) => toggleEnabled(row, value)"
							/>
						</td>
						<td class="px-1 py-2" @click.stop>
							<Dropdown :options="rowActions(row)">
								<Button variant="ghost">
									<template #icon><LucideEllipsisVertical class="size-4" /></template>
								</Button>
							</Dropdown>
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<CatalogCouponDialog v-model="showDialog" :edit-row="editRow" @saved="coupons.reload()" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Dropdown, Switch, call, createResource, dialog, toast } from 'frappe-ui'

import LucideEllipsisVertical from '~icons/lucide/ellipsis-vertical'
import LucidePencil from '~icons/lucide/pencil'
import LucidePlus from '~icons/lucide/plus'
import LucideTrash2 from '~icons/lucide/trash-2'

import CatalogCouponDialog, { type CouponRow } from '@/components/CatalogCouponDialog.vue'
import CatalogListState from '@/components/CatalogListState.vue'

const showDialog = ref(false)
const editRow = ref<CouponRow | null>(null)

const coupons = createResource({
	url: 'shop.api.discounts.get_coupons',
	auto: true,
})

const rows = computed<CouponRow[]>(() => coupons.data || [])

function validity(row: CouponRow) {
	if (!row.valid_from && !row.valid_upto) return 'Always valid'
	const from = row.valid_from ? formatDate(row.valid_from) : 'Any time'
	const to = row.valid_upto ? formatDate(row.valid_upto) : 'no end date'
	return `${from} to ${to}`
}

function formatDate(date: string) {
	return new Date(date).toLocaleDateString('en-GB', {
		day: 'numeric',
		month: 'short',
		year: 'numeric',
	})
}

function openNew() {
	editRow.value = null
	showDialog.value = true
}

function openEdit(row: CouponRow) {
	editRow.value = row
	showDialog.value = true
}

function rowActions(row: CouponRow) {
	return [
		{ label: 'Edit', icon: LucidePencil, onClick: () => openEdit(row) },
		{ label: 'Delete', icon: LucideTrash2, theme: 'red', onClick: () => confirmDelete(row) },
	]
}

function confirmDelete(row: CouponRow) {
	dialog.confirm({
		title: 'Delete coupon',
		message: `Delete coupon <b>${row.coupon_code}</b>? Shoppers can no longer use it.`,
		theme: 'red',
		confirmLabel: 'Delete',
		onConfirm: async () => {
			await call('shop.api.discounts.delete_coupon', { name: row.name })
			toast.success('Coupon deleted')
			coupons.reload()
		},
	})
}

async function toggleEnabled(row: CouponRow, value: boolean) {
	row.enabled = value
	try {
		await call('shop.api.discounts.set_enabled', { name: row.name, enabled: value })
	} catch (error) {
		row.enabled = !value
		toast.error('Could not update coupon')
	}
}
</script>
