import { test, expect } from '@playwright/test';

test('login page loads', async ({page}) => {
  await page.goto('/login');
  await expect(page.getByText('Bem-vindo de volta')).toBeVisible();
});
