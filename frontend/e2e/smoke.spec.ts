import { existsSync } from 'node:fs';
import { test, expect } from '@playwright/test';

test('login page loads', async ({page}) => {
  await page.goto('/login');
  await expect(page.getByText('Bem-vindo de volta')).toBeVisible();
});

test('register page validates required fields', async ({page}) => {
  await page.goto('/register');
  await expect(page.getByRole('heading', {name: 'Crie sua conta'})).toBeVisible();
  await page.getByRole('button', {name: 'CRIAR CONTA'}).click();
  await expect(page.getByText('Informe seu nome.')).toBeVisible();
  await expect(page.getByText('Informe um e-mail válido.')).toBeVisible();
  await expect(page.getByText('A senha deve ter pelo menos 8 caracteres.')).toBeVisible();
});

test('registers, opens the authenticated dashboard and logs out', async ({page}) => {
  const email = `e2e-${Date.now()}@example.com`;
  await page.goto('/register');
  await page.getByLabel('Nome').fill('E2E User');
  await page.getByLabel('E-mail').fill(email);
  await page.locator('#password').fill('DemoPass123!');
  await page.locator('#confirmPassword').fill('DemoPass123!');
  await page.getByRole('button', {name: 'CRIAR CONTA'}).click();

  await expect(page).toHaveURL(/dashboard/);
  await expect(page.getByText('Processamento de vídeos')).toBeVisible();
  await page.getByRole('button', {name: /Sair/}).click();
  await expect(page).toHaveURL(/login/);
});

test('authenticated upload, download and failure notification', async ({page}) => {
  test.setTimeout(60_000);
  const videoPath = process.env.FIAPX_E2E_VIDEO ?? 'C:/Users/Public/fiapx-demo.mp4';
  const invalidPath = process.env.FIAPX_E2E_INVALID_VIDEO ?? 'C:/Users/Public/fiapx-invalid.mp4';
  test.skip(!existsSync(videoPath) || !existsSync(invalidPath), 'runtime video fixtures are not available');

  const email = `e2e-flow-${Date.now()}@example.com`;
  await page.goto('/register');
  await page.getByLabel('Nome').fill('E2E Flow User');
  await page.getByLabel('E-mail').fill(email);
  await page.locator('#password').fill('DemoPass123!');
  await page.locator('#confirmPassword').fill('DemoPass123!');
  await page.getByRole('button', {name: 'CRIAR CONTA'}).click();
  await expect(page).toHaveURL(/dashboard/);

  await page.getByRole('link', {name: /NOVO VÍDEO/}).click();
  await expect(page.getByRole('dialog', {name: 'Enviar novos vídeos'})).toBeVisible();
  await page.locator('input[type=file]').setInputFiles(videoPath);
  await page.getByRole('button', {name: 'ENVIAR', exact: true}).click();
  const completedCard = page.locator('.video-card').filter({hasText: 'fiapx-demo.mp4'});
  await expect(completedCard.getByText('Concluído')).toBeVisible({timeout: 20000});
  const downloadPromise = page.waitForEvent('download');
  await completedCard.getByRole('button', {name: 'Baixar ZIP'}).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('frames.zip');

  await page.getByRole('link', {name: /NOVO VÍDEO/}).click();
  await expect(page.getByRole('dialog', {name: 'Enviar novos vídeos'})).toBeVisible();
  await page.locator('input[type=file]').setInputFiles(invalidPath);
  await page.getByRole('button', {name: 'ENVIAR', exact: true}).click();
  await expect(page.getByText('Falhas')).toBeVisible({timeout: 20000});
  await page.getByRole('button', {name: 'Notificações'}).click();
  await expect(page.getByText(/Falha ao processar o vídeo/)).toBeVisible({timeout: 10000});
});
