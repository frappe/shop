<template>
	<div class="mx-auto max-w-5xl px-6 pb-20">
		<CatalogProductHeader
			:title="title"
			:save-label="isEdit ? 'Save' : 'Create'"
			:dirty="dirty"
			:saving="saving"
			:storefront-url="storefrontUrl"
			@save="save"
		/>

		<CatalogProductSkeleton v-if="loading" />

		<div v-else-if="loadError" class="flex flex-col items-center gap-3 py-24 text-center">
			<p class="text-p-base text-ink-red-8">Could not load this product.</p>
			<Button @click="load">Try again</Button>
		</div>

		<div v-else class="mt-6 grid items-start gap-6 lg:grid-cols-3">
			<div class="space-y-6 lg:col-span-2">
				<CatalogSection
					v-if="isLink"
					title="Item"
					description="Pick the item you already sell in ERPNext."
				>
					<CatalogItemPicker @picked="onItemPicked" />
				</CatalogSection>

				<CatalogSection title="Basics">
					<FormControl v-model="form.product_name" label="Product name" required />
					<FormControl v-if="isEdit" v-model="form.slug" label="Slug" :description="slugHint" />
					<FormControl
						v-model="form.short_description"
						label="Short description"
						description="One line shown on product cards and in search results."
					/>
					<div>
						<label class="mb-1.5 block text-xs text-ink-gray-5">Description</label>
						<TextEditor
							:content="form.description"
							:bubble-menu="true"
							editor-class="prose-sm min-h-32 px-3 py-2 focus:outline-none"
							class="rounded border border-outline-gray-2 focus-within:border-outline-gray-3"
							placeholder="Tell shoppers what makes this product worth it"
							@change="(html: string) => (form.description = html)"
						/>
					</div>
				</CatalogSection>

				<CatalogSection title="Media">
					<CatalogImageListInput v-model="form.images" />
				</CatalogSection>

				<CatalogSection
					v-if="isEdit"
					id="variants"
					class="scroll-mt-20"
					title="Variants"
					description="Sell more than one version of this product."
				>
					<CatalogVariantsPanel :product="name!" :gallery="form.images" @updated="onVariantsUpdated" />
				</CatalogSection>

				<CatalogSection
					v-else-if="isCreate"
					title="Variants"
					description="Sell more than one version of this product."
				>
					<Switch
						v-model="withOptions"
						label="This product has options (like size or colour)"
						class="!w-auto"
					/>
					<CatalogOptionsEditor v-if="withOptions" v-model="options" />
				</CatalogSection>

				<CatalogSection title="Pricing">
					<p v-if="variantPricing" class="text-sm text-ink-gray-6">
						Prices are managed per variant. Set them in the Variants card
						<template v-if="isEdit">above.</template>
						<template v-else>after the product is created.</template>
					</p>
					<template v-else>
						<div class="grid gap-4 sm:grid-cols-2">
							<FormControl
								v-model.number="form.price"
								type="number"
								:label="withOptions ? 'Price per variant' : 'Price'"
							/>
							<FormControl
								v-if="!withOptions"
								v-model.number="form.compare_at_price"
								type="number"
								label="Compare-at price"
								description="Shown struck through on the storefront."
							/>
						</div>
						<p v-if="discountHint" class="text-sm text-ink-green-6">{{ discountHint }}</p>
					</template>
				</CatalogSection>

				<CatalogSection
					v-if="isEdit && detail?.item"
					title="Quantity breaks"
					description="Lower prices for buying more, for every customer. Trade accounts get their trade rates instead."
				>
					<PricingRates scope="everyone" :item="detail.item" :item-label="form.product_name" />
				</CatalogSection>

				<CatalogSection title="Highlights" description="One per line, shown next to the product.">
					<FormControl
						v-model="form.highlights"
						type="textarea"
						:rows="4"
						placeholder="Dishwasher safe"
					/>
				</CatalogSection>

				<CatalogSection
					title="Specifications"
					description="Shown as a table on the product page. Those set as filters let shoppers narrow a collection by them."
				>
					<div v-for="(row, index) in form.specifications" :key="index" class="flex items-end gap-2">
						<UiPicker
							v-model="row.specification"
							:label="index ? undefined : 'Specification'"
							:options="specificationNames"
							placeholder="Choose or type, e.g. Capacity"
							allow-custom
							class="flex-1"
						/>
						<FormControl
							v-model="row.value"
							:label="index ? undefined : 'Value'"
							placeholder="1 TB"
							class="flex-1"
						/>
						<Button variant="ghost" :aria-label="`Remove ${row.specification || 'specification'}`" @click="form.specifications.splice(index, 1)">
							<template #icon><LucideTrash2 class="size-4" /></template>
						</Button>
					</div>
					<Button class="w-fit" @click="form.specifications.push({ specification: '', value: '' })">
						Add specification
					</Button>
				</CatalogSection>
			</div>

			<div class="space-y-6 lg:sticky lg:top-16">
				<CatalogSection title="Status">
					<Switch v-model="form.published" label="Published" class="!w-auto" />
					<p class="text-sm text-ink-gray-6">
						Draft products stay out of the storefront until you publish them.
					</p>
				</CatalogSection>

				<CatalogSection title="Organization">
					<Autocomplete
						v-if="isEdit || !isLink"
						v-model="itemGroupValue"
						label="Item Group"
						placeholder="Select an Item Group"
						:options="itemGroupOptions"
					/>
					<UiPicker
						v-if="isEdit || !isLink"
						v-model="form.brand"
						label="Brand"
						description="A brand shoppers can filter by. Type a new one to add it."
						:options="brandNames"
						empty-label="No brand"
						allow-custom
					/>
					<Autocomplete
						v-model="collectionValue"
						label="Collections"
						placeholder="Select collections"
						:options="collectionOptions"
						multiple
					/>
					<FormControl
						v-model.number="form.ranking"
						type="number"
						label="Ranking"
						description="Higher ranked products appear first."
					/>
				</CatalogSection>

				<CatalogSection
					v-if="isEdit || !isLink"
					title="Shipping and tax"
					description="Kept on the product's ERPNext Item."
				>
					<FormControl
						v-model.number="form.weight"
						type="number"
						:label="`Weight per item (${form.weight_uom || 'kg'})`"
						description="Carriers price shipping by weight."
					/>
					<FormControl
						v-model="form.item_tax_template"
						type="select"
						label="Tax"
						:options="taxOptions"
						description="An Item Tax Template changes the tax rate for this product, e.g. zero-rated."
					/>
					<FormControl
						v-model="form.shipping_restriction"
						type="select"
						label="Ships to"
						:options="restrictionOptions"
						description="Where the store can send it. Restrictions are set up in Settings."
					/>
				</CatalogSection>

				<CatalogSection v-if="!isLink" title="Inventory">
					<Switch
						v-if="!isEdit"
						v-model="form.track_stock"
						label="Track stock"
						description="Off for services and digital products, which are never out of stock."
						class="!w-auto"
					/>
					<p v-else-if="detail && !detail.track_stock" class="text-sm text-ink-gray-6">
						This product's stock isn't tracked.
					</p>
					<CatalogStockControl
						v-if="isEdit && detail && detail.track_stock"
						:item-code="detail.item"
						:stock="detail.stock"
						:has-variants="!!detail.has_variants"
						@updated="onStockUpdated"
						@show-variants="showVariants"
					/>
					<FormControl
						v-else-if="!isEdit && form.track_stock"
						v-model.number="form.opening_stock"
						type="number"
						:label="withOptions ? 'Opening stock per variant' : 'Opening stock'"
					/>
				</CatalogSection>

				<CatalogSection v-if="isEdit" title="Danger zone">
					<p class="text-sm text-ink-gray-6">
						Deleting removes the product from the storefront. The underlying item is kept.
					</p>
					<Button theme="red" class="w-full" @click="confirmDelete">
						<template #prefix><LucideTrash2 class="size-4" /></template>
						Delete product
					</Button>
				</CatalogSection>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { Autocomplete, Button, FormControl, Switch, TextEditor, call, dialog, toast } from 'frappe-ui'

import LucideTrash2 from '~icons/lucide/trash-2'

import CatalogImageListInput from '@/components/CatalogImageListInput.vue'
import CatalogItemPicker from '@/components/CatalogItemPicker.vue'
import CatalogOptionsEditor, { optionsError, type ProductOption } from '@/components/CatalogOptionsEditor.vue'
import CatalogProductHeader from '@/components/CatalogProductHeader.vue'
import CatalogProductSkeleton from '@/components/CatalogProductSkeleton.vue'
import CatalogSection from '@/components/CatalogSection.vue'
import CatalogStockControl from '@/components/CatalogStockControl.vue'
import CatalogVariantsPanel from '@/components/CatalogVariantsPanel.vue'
import PricingRates from '@/components/PricingRates.vue'
import UiPicker from '@/components/UiPicker.vue'
import { storefrontPath } from '@/utils/storefront'

interface Option {
	label: string
	value: string
}

interface ProductDetail {
	name: string
	item: string
	slug: string
	has_variants: number
	stock: number
}

const props = defineProps<{ name?: string }>()

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!props.name)
const isLink = computed(() => !isEdit.value && route.query.mode === 'link')
const isCreate = computed(() => !isEdit.value && !isLink.value)

const loading = ref(true)
const loadError = ref(false)
const saving = ref(false)
const leaving = ref(false)
const baseline = ref('')
const detail = ref<ProductDetail | null>(null)
const collectionOptions = ref<Option[]>([])
const itemGroupOptions = ref<Option[]>([])
const itemTaxTemplates = ref<string[]>([])
const taxOptions = computed(() => [
	{ label: "The store's tax", value: '' },
	...itemTaxTemplates.value.map((name) => ({ label: name, value: name })),
])
const shippingRestrictions = ref<string[]>([])
const restrictionOptions = computed(() => [
	{ label: 'As its Item Group', value: '' },
	...shippingRestrictions.value.map((name) => ({ label: name, value: name })),
])
const defaultItemGroup = ref('')
const itemHasVariants = ref(false)
const withOptions = ref(false)
const options = ref<ProductOption[]>([{ attribute: '', values: [] }])

const form = reactive({
	item: '',
	product_name: '',
	slug: '',
	short_description: '',
	description: '',
	published: true,
	ranking: 0,
	price: null as number | null,
	compare_at_price: null as number | null,
	opening_stock: 0,
	highlights: '',
	images: [] as string[],
	collections: [] as string[],
	item_group: '',
	brand: '',
	specifications: [] as { specification: string; value: string }[],
	weight: 0,
	weight_uom: '',
	item_tax_template: '',
	shipping_restriction: '',
	track_stock: true,
})
const brandNames = ref<string[]>([])
const specificationNames = ref<string[]>([])

const title = computed(() => {
	if (isEdit.value) return form.product_name || 'Product'
	return isLink.value ? 'Link existing item' : 'New product'
})

const storefrontUrl = computed(() =>
	isEdit.value && detail.value?.slug ? storefrontPath(`product/${detail.value.slug}`) : undefined,
)

const slugHint = computed(() => `Storefront URL: ${storefrontPath(`product/${form.slug || detail.value?.slug || ''}`)}`)

const variantPricing = computed(() =>
	isEdit.value ? !!detail.value?.has_variants : isLink.value && itemHasVariants.value,
)

const discountHint = computed(() => {
	const price = Number(form.price)
	const compareAt = Number(form.compare_at_price)
	if (!price || !compareAt || compareAt <= price) return ''
	return `${Math.round((1 - price / compareAt) * 100)}% off the compare-at price`
})

const collectionValue = computed({
	get: () =>
		form.collections.map((name) => ({
			label: collectionOptions.value.find((option) => option.value === name)?.label || name,
			value: name,
		})),
	set: (selected: Option[]) => (form.collections = selected.map((option) => option.value)),
})

const itemGroupValue = computed({
	get: () => (form.item_group ? { label: form.item_group, value: form.item_group } : null),
	set: (selected: Option | null) => (form.item_group = selected?.value || defaultItemGroup.value),
})

const dirty = computed(() => !loading.value && snapshot() !== baseline.value)

watch(() => props.name, load, { immediate: true })

function snapshot() {
	return JSON.stringify({ ...form, withOptions: withOptions.value, options: options.value })
}

async function load() {
	loading.value = true
	loadError.value = false
	try {
		resetForm()
		await Promise.all([loadCollections(), loadItemGroups()])
		if (isEdit.value) await loadProduct(props.name as string)
		baseline.value = snapshot()
	} catch (error) {
		loadError.value = true
	} finally {
		loading.value = false
		leaving.value = false
	}
}

function resetForm() {
	Object.assign(form, {
		item: '',
		product_name: '',
		slug: '',
		short_description: '',
		description: '',
		published: true,
		ranking: 0,
		price: null,
		compare_at_price: null,
		opening_stock: 0,
		highlights: '',
		images: [],
		collections: [],
		item_group: '',
		brand: '',
		specifications: [],
		weight: 0,
		weight_uom: '',
		item_tax_template: '',
		shipping_restriction: '',
		track_stock: true,
	})
	detail.value = null
	itemHasVariants.value = false
	withOptions.value = false
	options.value = [{ attribute: '', values: [] }]
}

async function loadCollections() {
	const rows = await call('shop.api.products.get_collections')
	collectionOptions.value = rows.map((row: { name: string; title: string; parent_title: string | null }) => ({
		label: row.parent_title ? `${row.parent_title} › ${row.title}` : row.title,
		value: row.name,
	}))
}

async function loadItemGroups() {
	const result = await call('shop.api.products.get_item_groups')
	itemGroupOptions.value = result.item_groups.map((name: string) => ({ label: name, value: name }))
	defaultItemGroup.value = result.default
	if (!form.item_group) form.item_group = result.default
	itemTaxTemplates.value = result.item_tax_templates || []
	shippingRestrictions.value = result.shipping_restrictions || []
	brandNames.value = result.brands || []
	specificationNames.value = result.specifications || []
}

async function loadProduct(name: string) {
	const doc = await call('shop.api.products.get_product', { name })
	detail.value = doc
	Object.assign(form, {
		product_name: doc.product_name || '',
		slug: doc.slug || '',
		short_description: doc.short_description || '',
		description: doc.description || '',
		published: !!doc.published,
		ranking: doc.ranking || 0,
		price: doc.price,
		compare_at_price: doc.compare_at_price,
		highlights: doc.highlights || '',
		images: (doc.images || []).map((row: { image: string }) => row.image),
		collections: doc.collections || [],
		item_group: doc.item_group || '',
		brand: doc.brand || '',
		specifications: (doc.specifications || []).map((row: { specification: string; value: string }) => ({ ...row })),
		weight: doc.weight || 0,
		weight_uom: doc.weight_uom || '',
		item_tax_template: doc.item_tax_template || '',
		shipping_restriction: doc.shipping_restriction || '',
		track_stock: !!doc.track_stock,
	})
}

function onItemPicked(item: { label: string; value: string; hasVariants: boolean }) {
	form.item = item.value
	itemHasVariants.value = item.hasVariants
	if (!form.product_name) form.product_name = item.label
}

function onVariantsUpdated(hasVariants: boolean) {
	if (detail.value) detail.value.has_variants = hasVariants ? 1 : 0
}

function onStockUpdated(stock: number) {
	if (detail.value) detail.value.stock = stock
}

function showVariants() {
	document.getElementById('variants')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function save() {
	if (!form.product_name.trim()) {
		toast.error('Product name is required')
		return
	}
	saving.value = true
	try {
		if (isEdit.value) await saveExisting()
		else await createNew()
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not save product')
	} finally {
		saving.value = false
	}
}

async function saveExisting() {
	const doc = await call('shop.api.products.save_product', { payload: payload() })
	detail.value = doc
	form.slug = doc.slug || ''
	baseline.value = snapshot()
	toast.success('Product saved')
}

async function createNew() {
	const name = isLink.value ? await createFromItem() : await createFresh()
	// the product exists now: whatever follows, saving again mustn't make a second one
	let unsaved = ''
	if (!isLink.value) {
		try {
			await finishCreate(name)
		} catch (error) {
			unsaved = (error as { messages?: string[] }).messages?.[0] || 'Some details were not saved'
		}
	}
	baseline.value = snapshot()
	leaving.value = true
	if (unsaved) toast.warning(`Product created. ${unsaved}`)
	else toast.success('Product created')
	await router.replace(`/products/${encodeURIComponent(name)}`)
}

async function createFromItem() {
	if (!form.item) throw { messages: ['Select an item first'] }
	const doc = await call('shop.api.products.save_product', { payload: payload() })
	return doc.name as string
}

async function createFresh() {
	if (!form.price) throw { messages: ['Price is required'] }
	if (!withOptions.value) {
		const doc = await call('shop.api.products.create_product', {
			product_name: form.product_name,
			price: form.price,
			description: form.description,
			short_description: form.short_description,
			compare_at_price: form.compare_at_price || 0,
			opening_stock: form.opening_stock || 0,
			images: form.images,
			collections: form.collections,
			published: form.published,
			item_group: form.item_group,
			track_stock: form.track_stock,
		})
		return doc.name as string
	}
	const message = optionsError(options.value)
	if (message) throw { messages: [message] }
	const result = await call('shop.api.variants.create_variant_product', {
		product_name: form.product_name,
		options: options.value,
		price: form.price,
		opening_stock: form.opening_stock || 0,
		short_description: form.short_description,
		description: form.description,
		images: form.images,
		collections: form.collections,
		published: form.published,
		item_group: form.item_group,
		track_stock: form.track_stock,
	})
	return result.product as string
}

// create_product and create_variant_product take neither highlights, ranking, weight, tax nor
// shipping restriction.
async function finishCreate(name: string) {
	if (
		form.highlights ||
		form.ranking ||
		form.weight ||
		form.item_tax_template ||
		form.shipping_restriction ||
		form.brand ||
		form.specifications.length
	) {
		await call('shop.api.products.save_product', {
			payload: {
				name,
				brand: form.brand,
				specifications: form.specifications,
				highlights: form.highlights,
				ranking: form.ranking,
				published: form.published,
				weight: form.weight,
				item_tax_template: form.item_tax_template,
				shipping_restriction: form.shipping_restriction,
			},
		})
	}
	return name
}

function payload() {
	return {
		name: isEdit.value ? props.name : undefined,
		item: isLink.value ? form.item : undefined,
		product_name: form.product_name,
		slug: form.slug || undefined,
		short_description: form.short_description,
		description: form.description,
		compare_at_price: form.compare_at_price,
		highlights: form.highlights,
		ranking: form.ranking,
		published: form.published,
		images: form.images,
		collections: form.collections,
		item_group: isEdit.value ? form.item_group : undefined,
		brand: isEdit.value ? form.brand : undefined,
		specifications: form.specifications,
		weight: isEdit.value ? form.weight : undefined,
		item_tax_template: isEdit.value ? form.item_tax_template : undefined,
		shipping_restriction: isEdit.value ? form.shipping_restriction : undefined,
		price: variantPricing.value ? undefined : form.price,
	}
}

function confirmDelete() {
	dialog.confirm({
		title: 'Delete product',
		message: `Remove ${form.product_name} from the storefront? The underlying item is kept.`,
		theme: 'red',
		confirmLabel: 'Delete',
		onConfirm: async () => {
			await call('shop.api.products.delete_product', { name: props.name })
			toast.success('Product deleted')
			leaving.value = true
			router.push('/products')
		},
	})
}

onBeforeRouteLeave(() => {
	if (leaving.value || !dirty.value) return true
	return new Promise<boolean>((resolve) => {
		dialog.confirm({
			title: 'Discard changes?',
			message: 'This product has unsaved changes. Leaving now discards them.',
			theme: 'red',
			confirmLabel: 'Discard changes',
			cancelLabel: 'Keep editing',
			onConfirm: () => resolve(true),
			onCancel: () => resolve(false),
		})
	})
})
</script>
