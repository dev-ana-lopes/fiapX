import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

export interface BreadcrumbItem {
  label: string;
  route?: string;
}

@Component({
  selector: 'app-breadcrumbs',
  standalone: true,
  imports: [RouterLink],
  template: `<nav class="breadcrumbs" aria-label="Navegação estrutural"><ol>@for (item of items(); track item.label; let last = $last) {<li>@if (item.route && !last) {<a [routerLink]="item.route">{{item.label}}</a>} @else {<span [attr.aria-current]="last ? 'page' : null">{{item.label}}</span>} @if (!last) {<i aria-hidden="true">/</i>}</li>}</ol></nav>`,
})
export class BreadcrumbsComponent {
  readonly items = input.required<BreadcrumbItem[]>();
}
