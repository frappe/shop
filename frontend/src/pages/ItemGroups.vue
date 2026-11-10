<template>
	<div class="mx-auto max-w-6xl px-6 py-8">
		<UiPageHeader
			title="Item Groups"
			subtitle="How products are grouped in ERPNext, for reports, accounts and rates. A group's rates also cover the groups inside it."
		>
			<template #actions>
				<Button variant="solid" @click="openEditor()">
					<template #prefix><LucidePlus class="size-4" /></template>
					New Item Group
				</Button>
			</template>
		</UiPageHeader>

		<div v-if="tree.error" class="mt-6 flex flex-col items-center gap-3 py-16 text-center">
			<p class="text-p-base text-ink-red-8">{{ errorMessage(tree.error, 'Could not load the Item Groups') }}</p>
			<Button @click="tree.reload()">Try again</Button>
		</div>

		<div v-else class="mt-6 grid gap-6 lg:grid-cols-[18rem_1fr]">
			<nav class="h-fit rounded-lg border border-outline-gray-1 py-1" aria-label="Item Groups">
				<button
					v-for="group in groups"
					:key="group.name"
					type="button"
					class="flex w-full items-center justify-between gap-2 py-1.5 pr-3 text-left text-base"
					:class="group.name === selected ? 'bg-surface-gray-2 text-ink-gray-9' : 'text-ink-gray-7 hover:bg-surface-gray-1'"
					:style="{ paddingLeft: `${0.75 + (group.depth - 1) * 1}rem` }"
					:aria-current="group.name === selected ? 'true' : undefined"
					@click="select(group.name)"
				>
					<span class="truncate">{{ group.name }}</span>
					<span v-if="group.products" class="text-sm text-ink-gray-5">{{ group.products }}</span>
				</button>
			</nav>

			<div v-if="detail.data" class="min-w-0">
				<div class="flex flex-wrap items-start justify-between gap-3">
					<div>
						<h2 class="text-lg font-semibold text-ink-gray-9">{{ detail.data.name }}</h2>
						<p v-if="detail.data.parent" class="text-p-sm text-ink-gray-5">Inside {{ detail.data.parent }}</p>
					</div>
					<div class="flex flex-wrap gap-2">
						<Button variant="solid" @click="openAdding">
							<template #prefix><LucidePlus class="size-3.5" /></template>
							Add products
						</Button>
						<Button @click="openEditor(undefined, detail.data.name)">New group inside</Button>
						<Button v-if="detail.data.parent" @click="openEditor(selectedGroup)">Edit</Button>
						<Button
							v-if="detail.data.parent"
							theme="red"
							variant="ghost"
							:disabled="!!detail.data.products.length || !!detail.data.groups_inside.length"
							:title="detail.data.products.length || detail.data.groups_inside.length ? 'Move what is in it first' : ''"
							@click="confirmDelete"
						>
							Remove
						</Button>
					</div>
				</div>

				<p v-if="detail.data.groups_inside.length" class="mt-3 text-p-sm text-ink-gray-6">
					Groups inside:
					<template v-for="(name, index) in detail.data.groups_inside" :key="name">
						{{ index ? ', ' : '' }}<button type="button" class="underline" @click="select(name)">{{ name }}</button>
					</template>
				</p>

				<div class="mt-4 rounded-lg border border-outline-gray-1">
					<div v-if="!detail.data.products.length" class="px-4 py-10 text-center text-p-base text-ink-gray-5">
						No products in this group. Use Add products to put some in it.
					</div>
					<div
						v-for="product in detail.data.products"
						:key="product.item_code"
						class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-2.5 last:border-b-0"
					>
						<img
							v-if="product.image"
							:src="product.image"
							alt=""
							class="size-9 shrink-0 rounded bg-surface-gray-1 object-cover"
						/>
						<div v-else class="size-9 shrink-0 rounded bg-surface-gray-1" />
						<div class="min-w-0 flex-1">
							<router-link
								v-if="product.product"
								:to="`/products/${encodeURIComponent(product.product)}`"
								class="font-medium text-ink-gray-8 hover:underline"
							>
								{{ product.name }}
							</router-link>
							<span v-else class="font-medium text-ink-gray-8">{{ product.name }}</span>
							<div class="text-sm text-ink-gray-5">{{ product.item_code }}</div>
						</div>
						<UiStatusBadge :label="productStatus(product)" />
						<Button variant="ghost" @click="openMoving(product)">Move</Button>
					</div>
				</div>
			</div>

			<div v-else-if="detail.loading" class="flex justify-center py-20"><Spinner class="size-5" /></div>
		</div>

		<Dialog
			v-model="editing"
			:options="{
				title: form.name ? `Edit ${form.name}` : 'New Item Group',
				actions: [{ label: 'Save', variant: 'solid', loading: saving, onClick: save }],
			}"
		>
			<div class="space-y-4">
				<FormControl v-model="form.item_group_name" label="Name" required />
				<UiPicker v-model="form.parent" label="Inside" description="The Item Group this one sits in." :options="parentOptions" />
				<p v-if="form.name" class="text-p-sm text-ink-gray-5">
					Renaming keeps the products, rates and records that use it.
				</p>
			</div>
		</Dialog>

		<Dialog
			v-model="moving"
			:options="{
				title: `Move ${movingProduct?.name || ''}`,
				actions: [{ label: 'Move', variant: 'solid', loading: saving, disabled: !moveTo, onClick: moveProduct }],
			}"
		>
			<UiPicker v-model="moveTo" label="To" description="The Item Group the chosen products move to." :options="groupOptions" />
		</Dialog>

		<Dialog
			v-model="adding"
			:options="{
				title: `Add products to ${selected}`,
				actions: [
					{
						label: chosen.length ? `Add ${chosen.length}` : 'Add',
						variant: 'solid',
						disabled: !chosen.length,
						loading: saving,
						onClick: addProducts,
					},
				],
			}"
		>
			<div class="space-y-3">
				<FormControl
					v-model="search"
					type="text"
					placeholder="Search products"
					aria-label="Search products"
					@update:model-value="findProducts"
				/>
				<div class="max-h-80 overflow-y-auto rounded border border-outline-gray-1">
					<p v-if="!found.length" class="px-3 py-6 text-center text-p-sm text-ink-gray-5">
						{{ search ? 'No products found' : 'Type to find products' }}
					</p>
					<label
						v-for="product in found"
						:key="product.item"
						class="flex cursor-pointer items-center gap-3 border-b border-outline-gray-1 px-3 py-2 last:border-b-0"
					>
						<input v-model="chosen" type="checkbox" :value="product.item" />
						<span class="min-w-0 flex-1">
							<span class="text-base text-ink-gray-8">{{ product.product_name }}</span>
							<span class="block text-sm text-ink-gray-5">
								{{ product.item }}<template v-if="product.item_group"> &middot; now in {{ product.item_group }}</template>
							</span>
						</span>
					</label>
				</div>
			</div>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Button, Dialog, FormControl, Spinner, call, createResource, dialog, toast } from 'frappe-ui'
import { useRoute, useRouter } from 'vue-router'

import LucidePlus from '~icons/lucide/plus'

import UiPageHeader from '@/components/UiPageHeader.vue'
import UiPicker from '@/components/UiPicker.vue'
import UiStatusBadge from '@/components/UiStatusBadge.vue'

interface ItemGroup {
	name: string
	parent: string | null
	depth: number
	products: number
	children: boolean
}

interface GroupProduct {
	item_code: string
	name: string
	product: string | null
	published: number
	disabled: number
}

const route = useRoute()
const router = useRouter()

const tree = createResource({ url: 'shop.api.products.get_item_group_tree', auto: true })
const groups = computed<ItemGroup[]>(() => tree.data || [])
const selected = ref(String(route.query.group || ''))
const selectedGroup = computed(() => groups.value.find((group) => group.name === selected.value))

const detail = createResource({
	url: 'shop.api.products.get_item_group',
	makeParams: () => ({ name: selected.value }),
})

function select(name: string) {
	selected.value = name
	router.replace({ query: { ...route.query, group: name } })
}

watch(selected, (name) => name && detail.reload())
watch(groups, (list) => {
	if (list.length && !list.some((group) => group.name === selected.value)) {
		select(list.find((group) => group.parent)?.name || list[0].name)
	} else if (selected.value && !detail.data) {
		detail.reload()
	}
})

function errorMessage(error: unknown, fallback: string) {
	const messages = (error as { messages?: string[] } | null)?.messages
	return messages?.[0] || fallback
}

function productStatus(product: GroupProduct) {
	if (product.disabled) return 'Disabled'
	if (!product.product) return 'Not in the store'
	return product.published ? 'Published' : 'Draft'
}

const groupOptions = computed(() =>
	groups.value.map((group) => ({
		label: `${'  '.repeat(group.depth - 1)}${group.name}`,
		value: group.name,
	})),
)

const saving = ref(false)

// edit or make a group
const editing = ref(false)
const form = reactive({ name: '', item_group_name: '', parent: '' })

// a group can't go inside itself or one of its own groups
const parentOptions = computed(() => {
	const all = groups.value
	const start = all.findIndex((group) => group.name === form.name)
	const inside = new Set<string>()
	if (start >= 0) {
		inside.add(form.name)
		for (const group of all.slice(start + 1)) {
			if (group.depth <= all[start].depth) break
			inside.add(group.name)
		}
	}
	return groupOptions.value.filter((option) => !inside.has(option.value))
})

function openEditor(group?: ItemGroup, parent?: string) {
	Object.assign(form, {
		name: group?.name || '',
		item_group_name: group?.name || '',
		parent: group?.parent || parent || groups.value[0]?.name || '',
	})
	editing.value = true
}

async function save() {
	saving.value = true
	try {
		const renamed = form.name && form.item_group_name.trim() !== form.name
		tree.data = await call('shop.api.products.save_item_group', {
			name: form.name || undefined,
			item_group_name: form.item_group_name,
			parent: form.parent,
		})
		editing.value = false
		toast.success('Item Group saved')
		select(renamed || !form.name ? form.item_group_name.trim() : form.name)
		detail.reload()
	} catch (error) {
		toast.error(errorMessage(error, 'Could not save the Item Group'))
	} finally {
		saving.value = false
	}
}

function confirmDelete() {
	const name = selected.value
	dialog.confirm({
		title: 'Remove Item Group',
		message: `Remove ${name}?`,
		theme: 'red',
		confirmLabel: 'Remove',
		onConfirm: async () => {
			try {
				tree.data = await call('shop.api.products.delete_item_group', { name })
				toast.success('Item Group removed')
			} catch (error) {
				toast.error(errorMessage(error, 'Could not remove the Item Group'))
			}
		},
	})
}

// move one product elsewhere
const moving = ref(false)
const movingProduct = ref<GroupProduct | null>(null)
const moveTo = ref('')

function openMoving(product: GroupProduct) {
	movingProduct.value = product
	moveTo.value = ''
	moving.value = true
}

async function moveProduct() {
	if (!movingProduct.value || !moveTo.value) return
	saving.value = true
	try {
		await call('shop.api.products.move_products', {
			item_codes: [movingProduct.value.item_code],
			item_group: moveTo.value,
		})
		moving.value = false
		toast.success(`Moved to ${moveTo.value}`)
		detail.reload()
		tree.reload()
	} catch (error) {
		toast.error(errorMessage(error, 'Could not move the product'))
	} finally {
		saving.value = false
	}
}

// bring products into this group
const adding = ref(false)
const search = ref('')
const found = ref<{ item: string; product_name: string; item_group?: string }[]>([])
const chosen = ref<string[]>([])
let searchTimer: ReturnType<typeof setTimeout> | undefined

function openAdding() {
	search.value = ''
	found.value = []
	chosen.value = []
	adding.value = true
}

function findProducts(text: string) {
	clearTimeout(searchTimer)
	if (!text || text.length < 2) {
		found.value = []
		return
	}
	searchTimer = setTimeout(async () => {
		const result = (await call('shop.api.products.get_products', { search: text, limit: 20 })) as {
			products: { item: string; product_name: string; item_group?: string }[]
		}
		found.value = result.products.filter((product) => product.item && product.item_group !== selected.value)
	}, 250)
}

async function addProducts() {
	saving.value = true
	try {
		detail.data = await call('shop.api.products.move_products', {
			item_codes: chosen.value,
			item_group: selected.value,
		})
		adding.value = false
		toast.success(`Added ${chosen.value.length} to ${selected.value}`)
		tree.reload()
	} catch (error) {
		toast.error(errorMessage(error, 'Could not add the products'))
	} finally {
		saving.value = false
	}
}
</script>
