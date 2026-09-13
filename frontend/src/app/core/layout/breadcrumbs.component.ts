import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { RouterLink } from "@angular/router";

export interface BreadcrumbItem {
  label: string;
  route?: string;
}

@Component({
  selector: "app-breadcrumbs",
  standalone: true,
  imports: [RouterLink],
  templateUrl: "./breadcrumbs.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BreadcrumbsComponent {
  readonly items = input.required<BreadcrumbItem[]>();
}
