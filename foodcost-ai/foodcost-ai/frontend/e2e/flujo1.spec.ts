import { expect, test } from '@playwright/test'

// Flujo 1 de extremo a extremo (UI -> API -> PostgreSQL -> API -> UI):
// registrar ingrediente -> registrar compra -> crear receta -> agregar componente -> ver costo,
// margen y Food Cost -> registrar un precio nuevo y ver la receta recalculada.
// Usar sobre una base recién cargada con `python -m app.seed`. Para repetirla sin
// reiniciar la base, define E2E_SUFIJO (los nombres de ingredientes y recetas son únicos).
const sufijo = process.env.E2E_SUFIJO ? ` ${process.env.E2E_SUFIJO}` : ''
const ING = `Limón Tahití${sufijo}`
const REC = `Limonada natural${sufijo}`
const shot = (name: string) => `../docs/evidencias/${name}.png`

test('flujo 1: costear una receta de extremo a extremo', async ({ page }) => {
  // 1. Registrar ingrediente con merma
  await page.goto('/ingredientes')
  await page.fill('#ing-nombre', ING)
  await page.selectOption('#ing-unidad', { label: 'gramo (g)' })
  await page.fill('#ing-merma', '45')
  await page.screenshot({ path: shot('01-nuevo-ingrediente'), fullPage: true })
  await page.click('text=Guardar y registrar compra')

  // 2. Registrar la compra (2 kg por $15.000 -> $7.500/kg)
  await expect(page.locator('h1')).toHaveText(ING)
  await page.fill('#compra-cantidad', '2')
  await page.selectOption('#compra-unidad', { label: 'kg' })
  await page.fill('#compra-precio', '15000')
  await page.selectOption('#compra-proveedor', { label: 'Bazurto mayorista' })
  await page.click('button:has-text("Registrar compra")')
  await expect(page.locator('.aviso.ok')).toContainText('$7.500/kg')
  await page.screenshot({ path: shot('02-compra-registrada'), fullPage: true })

  // 3. Crear la receta con precio de venta
  await page.goto('/recetas')
  await page.fill('#rec-nombre', REC)
  await page.fill('#rec-pv', '6500')
  await page.fill('#rec-margen', '75')
  await page.click('text=Crear y agregar ingredientes')

  // 4. Agregar componentes: 90 g de limón (+ azúcar ya existente si hay)
  await expect(page.locator('h1')).toHaveText(REC)
  await page.selectOption('#comp-sel', { label: ING })
  await page.fill('#comp-cant', '90')
  await page.click('button:has-text("Agregar")')

  // 5. Verificar el cálculo: 90 g x $7,5/g / (1 - 0,45) = $1.227,27 -> Food Cost 18,9 %
  await expect(page.locator('.kpi').first()).toContainText('$1.227')
  await expect(page.locator('.kpi', { hasText: 'Food Cost' })).toContainText('18,9%')
  await expect(page.locator('.kpi', { hasText: 'Estado' })).toContainText('Rentable')
  await page.screenshot({ path: shot('03-receta-costeada'), fullPage: true })

  // 6. Sube el limón: nueva compra 2 kg por $21.000 ($10.500/kg, +40 %)
  await page.goto('/ingredientes')
  await page.click(`text=${ING}`)
  await page.fill('#compra-cantidad', '2')
  await page.selectOption('#compra-unidad', { label: 'kg' })
  await page.fill('#compra-precio', '21000')
  await page.click('button:has-text("Registrar compra")')
  await expect(page.locator('.aviso.ok')).toContainText('+40,0%')
  await expect(page.locator('.aviso.ok')).toContainText(REC)
  await page.screenshot({ path: shot('04-nuevo-precio-recalcula'), fullPage: true })

  // 7. La receta ya muestra el costo nuevo: 90 x 10,5 / 0,55 = $1.718,18 -> 26,4 %
  await page.goto('/recetas')
  await page.click(`text=${REC}`)
  await expect(page.locator('.kpi').first()).toContainText('$1.718')
  await expect(page.locator('.kpi', { hasText: 'Food Cost' })).toContainText('26,4%')
  await page.screenshot({ path: shot('05-receta-recalculada'), fullPage: true })

  // 8. Vista general de rentabilidad
  await page.goto('/')
  await expect(page.getByRole('cell', { name: REC })).toBeVisible()
  await page.screenshot({ path: shot('06-rentabilidad'), fullPage: true })
})
