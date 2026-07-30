<template>
	<div class="mt-6 grid animate-pulse items-start gap-6 lg:grid-cols-3">
		<div class="space-y-6 lg:col-span-2">
			<div v-for="card in [4, 2, 3]" :key="card" class="rounded-lg border border-outline-gray-1 p-5">
				<div class="h-4 w-32 rounded bg-surface-gray-3" />
				<div class="mt-4 space-y-3">
					<div v-for="line in card" :key="line" class="h-8 rounded bg-surface-gray-2" />
				</div>
			</div>
		</div>
		<div class="space-y-6">
			<div v-for="card in [2, 3]" :key="card" class="rounded-lg border border-outline-gray-1 p-5">
				<div class="h-4 w-24 rounded bg-surface-gray-3" />
				<div class="mt-4 space-y-3">
					<div v-for="line in card" :key="line" class="h-8 rounded bg-surface-gray-2" />
				</div>
			</div>
		</div>
	</div>
</template>
