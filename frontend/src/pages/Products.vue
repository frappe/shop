<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<div class="flex items-center justify-between">
			<h1 class="text-xl font-semibold text-ink-gray-9">Products</h1>
			<div class="flex gap-2">
				<Button @click="openDialog('link')">Link existing item</Button>
				<Button variant="solid" @click="openDialog('create')">
					<template #prefix><LucidePlus class="size-4" /></template>
					Add product
				</Button>
			</div>
		</div>

		<div class="mt-6 flex items-center justify-between gap-4">
			<FormControl
				v-model="search"
				type="text"
				placeholder="Search products"
				class="w-64"
				:debounce="300"
			>
				<template #prefix><LucideSearch class="size-4 text-ink-gray-5" /></template>
			</FormControl>
			<TabButtons v-model="status" :options="statusTabs" />
		</div>

		<CatalogListState
			:loading="products.loading && !products.data"
			:error="products.error"
			:empty="!rows.length"
			empty-title="No products found"
			empty-subtitle="Add a product or adjust your filters."
			@retry="products.reload()"
		>
			<template #action>
				<Button variant="solid" @click="openDialog('create')">Add product</Button>
			</template>
		</CatalogListState>

		<template v-if="rows.length && !products.error">
			<div class="mt-4 overflow-hidden rounded-lg border border-outline-gray-1">
				<table class="w-full text-base">
					<thead>
						<tr class="border-b border-outline-gray-1 text-left text-sm text-ink-gray-5">
							<th class="w-14 px-3 py-2 font-normal"></th>
							<th class="px-3 py-2 font-normal">Product</th>
							<th class="px-3 py-2 text-right font-normal">Price</th>
							<th class="px-3 py-2 text-right font-normal">Stock</th>
							<th class="px-3 py-2 text-right font-normal">Published</th>
							<th class="w-10 px-1 py-2"></th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row in rows"
							:key="row.name"
							class="cursor-pointer border-b border-outline-gray-1 last:border-b-0 hover:bg-surface-gray-1"
							@click="openEdit(row.name)"
						>
							<td class="px-3 py-2">
								<div
									class="flex size-9 items-center justify-center overflow-hidden rounded border border-outline-gray-1 bg-surface-gray-1"
								>
									<img
										v-if="row.image"
										:src="row.image"
										:alt="row.product_name"
										class="size-full object-cover"
									/>
									<LucideImage v-else class="size-4 text-ink-gray-4" />
								</div>
							</td>
							<td class="px-3 py-2">
								<div class="font-medium text-ink-gray-8">{{ row.product_name }}</div>
								<div class="text-sm text-ink-gray-5">/{{ row.slug }}</div>
							</td>
							<td class="px-3 py-2 text-right text-ink-gray-7">{{ row.formatted_price }}</td>
							<td
								class="px-3 py-2 text-right"
								:class="row.stock ? 'text-ink-gray-7' : 'font-medium text-ink-red-4'"
							>
								{{ row.stock }}
							</td>
							<td class="px-3 py-2 text-right" @click.stop>
								<Switch
									:model-value="!!row.published"
									@update:model-value="(value: boolean) => togglePublished(row, value)"
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
			<CatalogPagination
				:start="start"
				:limit="PAGE_SIZE"
				:total="products.data?.total || 0"
				@update:start="start = $event"
			/>
		</template>

		<ProductDialog v-model="showDialog" :mode="dialogMode" :edit-name="editName" @saved="products.reload()" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Dropdown, FormControl, Switch, TabButtons, call, createResource, dialog, toast } from 'frappe-ui'

import LucideEllipsisVertical from '~icons/lucide/ellipsis-vertical'
import LucideExternalLink from '~icons/lucide/external-link'
import LucideImage from '~icons/lucide/image'
import LucidePencil from '~icons/lucide/pencil'
import LucidePlus from '~icons/lucide/plus'
import LucideSearch from '~icons/lucide/search'
import LucideTrash2 from '~icons/lucide/trash-2'

import CatalogListState from '@/components/CatalogListState.vue'
import CatalogPagination from '@/components/CatalogPagination.vue'
import ProductDialog from '@/components/ProductDialog.vue'

interface ProductRow {
	name: string
	product_name: string
	slug: string
	published: number
	image: string | null
	formatted_price: string
	stock: number
}

const PAGE_SIZE = 20

const route = useRoute()
const search = ref((route.query.search as string) || '')
const status = ref('')
const start = ref(0)
const showDialog = ref(false)
const dialogMode = ref<'create' | 'link' | 'edit'>('create')
const editName = ref<string | null>(null)

const statusTabs = [
	{ label: 'All', value: '' },
	{ label: 'Published', value: 'published' },
	{ label: 'Draft', value: 'draft' },
]

const products = createResource({
	url: 'shop.api.products.get_products',
	makeParams: () => ({
		search: search.value || undefined,
		status: status.value || undefined,
		start: start.value,
		limit: PAGE_SIZE,
	}),
	auto: true,
})

const rows = computed<ProductRow[]>(() => products.data?.products || [])

watch([search, status], () => {
	start.value = 0
	products.reload()
})
watch(start, () => products.reload())

function openDialog(mode: 'create' | 'link') {
	dialogMode.value = mode
	editName.value = null
	showDialog.value = true
}

function openEdit(name: string) {
	dialogMode.value = 'edit'
	editName.value = name
	showDialog.value = true
}

function rowActions(row: ProductRow) {
	return [
		{ label: 'Edit', icon: LucidePencil, onClick: () => openEdit(row.name) },
		{
			label: 'View on storefront',
			icon: LucideExternalLink,
			onClick: () => window.open(`/product/${row.slug}`, '_blank'),
		},
		{ label: 'Delete', icon: LucideTrash2, theme: 'red', onClick: () => confirmDelete(row) },
	]
}

function confirmDelete(row: ProductRow) {
	dialog.confirm({
		title: 'Delete product',
		message: `Remove <b>${row.product_name}</b> from the storefront? The underlying item is kept.`,
		theme: 'red',
		confirmLabel: 'Delete',
		onConfirm: async () => {
			await call('shop.api.products.delete_product', { name: row.name })
			toast.success('Product deleted')
			products.reload()
		},
	})
}

async function togglePublished(row: ProductRow, value: boolean) {
	row.published = value ? 1 : 0
	try {
		await call('shop.api.products.set_published', { name: row.name, published: value })
	} catch (error) {
		row.published = value ? 0 : 1
		toast.error('Could not update product')
	}
}
</script>
