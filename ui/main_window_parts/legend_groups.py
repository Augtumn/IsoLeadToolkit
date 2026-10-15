"""Legend UI actions for main window."""
from __future__ import annotations

import logging
from typing import Any

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QCursor
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from core import app_state, state_gateway, translate
from ui.icons import apply_color_swatch
from visualization.line_styles import resolve_line_style
from visualization.plotting.legend_model import OVERLAY_TOGGLE_MAP

#: Methods this class expects from the classes it is composed with
#: (explicit interface, UI review item I).
REQUIRES_MainWindowLegendGroupMixin = (
    "_reload_legend_panel",
    "_set_legend_item_meta",
    "_show_parent_shape_menu",
    "_update_parent_swatch",
)

logger = logging.getLogger(__name__)


class MainWindowLegendGroupMixin:
    """Parent/child group structure of the legend."""

    def _current_parent_groups(self):
        return {
            str(k): list(v or []) for k, v in (app_state.parent_groups or {}).items()
        }

    #: Grouping column holding the labels a decomposition produces. As far as the rest of
    #: the application is concerned it is an ordinary grouping column.
    DECOMPOSED_GROUP_COLUMN = "__decomposed_group__"

    #: Reserved key in the decomposition map holding the column the chain starts from. It is
    #: prefixed with the path separator so it can never collide with a real path: a real path
    #: never starts with the separator, because an empty value is not a path.
    BASE_DECOMPOSITION_KEY = "\x1fbase_column"

    def _decomposition_spec(self):
        """Return ``({path key -> splitting column}, base column)`` from the stored map."""
        spec = dict(app_state.group_decomposition or {})
        base = spec.pop(self.BASE_DECOMPOSITION_KEY, None)
        return spec, (str(base) if base else None)

    def _path_of_label(self, label):
        """The value path a legend label stands for, e.g. ``Tarim / casting`` -> two values."""
        from visualization.plotting.decomposition import SEPARATOR

        return tuple(str(label).split(SEPARATOR))

    def _write_decomposition(self, spec, base) -> bool:
        """Materialise *spec* into the grouping column and the parent map.

        The labels become an ordinary column and the parent/child map goes through
        ``set_parent_groups``, so the plot, the legend, the colours, the per-parent marker
        shape and the visibility checkboxes all keep using the pipeline that is already there.
        """
        from visualization.plotting.decomposition import decompose, validate_spec

        frame = app_state.df_global
        if frame is None or not base or base not in frame.columns:
            QMessageBox.warning(
                self, translate("Warning"), translate("Please load data first.")
            )
            return False
        if not spec:
            # Nothing is decomposed: drop the column and go back to the original grouping.
            parents = {
                str(k): [c for c in list(v or []) if c in set(app_state.available_groups or [])]
                for k, v in (app_state.parent_groups or {}).items()
            }
            state_gateway.set_group_decomposition({})
            state_gateway.set_parent_groups(
                {k: v for k, v in parents.items() if v}
            )
            if self.DECOMPOSED_GROUP_COLUMN in frame.columns:
                state_gateway.set_dataframe_and_source(
                    frame.drop(columns=[self.DECOMPOSED_GROUP_COLUMN]),
                    file_path=app_state.file_path,
                    sheet_name=app_state.sheet_name,
                )
                columns = [c for c in (app_state.group_cols or [])
                           if c != self.DECOMPOSED_GROUP_COLUMN]
                state_gateway.set_group_data_columns(columns, list(app_state.data_cols or []))
            if base in (app_state.group_cols or []):
                state_gateway.set_last_group_col(base)
            # Visibility is left as it is: the labels that disappeared with the step are filtered
            # out when the group list is synced, so ticking everything is never the answer.
            state_gateway.bump_data_version()
            self._reload_legend_panel()
            self._refresh_after_decomposition(spec)
            return True

        try:
            validate_spec(frame, base, spec)
            labels, children = decompose(frame, base, spec)
        except (KeyError, ValueError, TypeError) as err:
            # The repository bans silent fallbacks: say what is wrong instead of skipping it.
            QMessageBox.warning(self, translate("Warning"), str(err))
            return False

        decomposed = frame.copy()
        decomposed[self.DECOMPOSED_GROUP_COLUMN] = list(labels)
        state_gateway.set_dataframe_and_source(
            decomposed, file_path=app_state.file_path, sheet_name=app_state.sheet_name
        )
        columns = list(app_state.group_cols or [])
        if self.DECOMPOSED_GROUP_COLUMN not in columns:
            columns.append(self.DECOMPOSED_GROUP_COLUMN)
        state_gateway.set_group_data_columns(columns, list(app_state.data_cols or []))
        parents = dict(app_state.parent_groups or {})
        parents.update(children)
        # Every parent this feature made comes from a path in the specification, so the ones the
        # specification no longer names are dropped rather than merged over: collapsing a step has
        # to remove the group it created, not leave it behind.
        from visualization.plotting.decomposition import SEPARATOR as _SEP, path_values

        previous = dict(app_state.group_decomposition or {})
        previous.pop(self.BASE_DECOMPOSITION_KEY, None)
        for key in previous:
            parents.pop(_SEP.join(path_values(key)), None)
        parents.update(children)
        state_gateway.set_parent_groups({k: v for k, v in parents.items() if v})
        state_gateway.set_group_decomposition({self.BASE_DECOMPOSITION_KEY: base, **spec})
        state_gateway.set_last_group_col(self.DECOMPOSED_GROUP_COLUMN)
        # Keep the selection the user had instead of ticking everything: a group that was visible
        # becomes the children it was refined into, and one that was hidden stays hidden.
        current = app_state.visible_groups
        if current is not None:
            visible = set(current)
            for label, kids in children.items():
                if label in visible:
                    visible.discard(label)
                    visible.update(kids)
            state_gateway.set_visible_groups(sorted(visible))
        state_gateway.bump_data_version()
        self._reload_legend_panel()
        self._refresh_after_decomposition(spec)
        return True

    def _refresh_after_decomposition(self, spec) -> None:
        try:
            from visualization.events import on_slider_change

            on_slider_change()
        except Exception as err:  # pragma: no cover - headless harness
            logger.warning("Could not refresh the plot after decomposing: %s", err)
        logger.info("Legend decomposition is now %s", spec or "(none)")

    def decompose_group_by(self, parent, by_column) -> bool:
        """Refine legend entry *parent* by *by_column*, inside itself.

        The entry is named by the path of values that leads to it, so splitting a child
        refines that child alone and leaves its siblings - and its ancestors' other
        branches - exactly as they were.
        """
        from visualization.plotting.decomposition import path_key

        spec, base = self._decomposition_spec()
        if base is None:
            base = app_state.last_group_col
        # The column a previous split produced is a valid base: refining a group step by step is
        # what this feature is for, and that column is materialised in the frame like any other.
        # Only having no grouping column at all leaves nothing to split from.
        if base is None or base not in [
            *(app_state.group_cols or []),
            self.DECOMPOSED_GROUP_COLUMN,
        ]:
            # No base to split from: the active column is the one a previous split produced.
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("Choose a grouping column before decomposing."),
            )
            return False
        # The dialog disables these columns and the method refuses them too: one that is constant
        # inside this group could only ever produce a single child, and reaching the same state by
        # another route must not do it silently.
        if str(by_column) in self._used_decomposition_columns(parent):
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("That column is already in use on this group's path."),
            )
            return False
        spec[path_key(self._path_of_label(parent))] = str(by_column)
        return self._write_decomposition(spec, base)
    def clear_group_decomposition(self, parent=None) -> bool:
        """Undo the decomposition of *parent* and everything split inside it.

        The split of a group is what defines its children, so clearing it has to clear the
        steps taken inside those children as well; otherwise they would name paths that no
        longer exist.
        """
        from visualization.plotting.decomposition import PATH_SEPARATOR, path_key, path_values

        spec, base = self._decomposition_spec()
        if parent is None:
            spec = {}
        else:
            prefix = self._path_of_label(parent)
            spec = {
                key: column
                for key, column in spec.items()
                if tuple(path_values(key))[: len(prefix)] != prefix
            }
        return self._write_decomposition(spec, base)

    def _decomposition_columns(self):
        """Every column the data can be grouped by, in offered order.

        The declared grouping columns come first, then any other column the data holds. The
        computed column a previous split produced is not offered; nothing else is filtered
        out, because which columns make sense to refine by is the user's call.
        """
        frame = app_state.df_global
        if frame is None:
            return []
        candidates: list[str] = []
        for column in [*(app_state.group_cols or []), *frame.columns]:
            name = str(column)
            if name in candidates or name not in frame.columns:
                continue
            if name == self.DECOMPOSED_GROUP_COLUMN:
                continue
            candidates.append(name)
        return candidates

    def _used_decomposition_columns(self, parent=None):
        """Columns that cannot refine *parent*: those already used **on its own path**.

        The active grouping column and the column of every step that produced this group are
        constant inside it, so refining by one of them could only ever yield a single child -
        that is why they are locked here. A column used in another branch is not restricted:
        nothing about that branch says anything about this one.
        """
        from visualization.plotting.decomposition import path_key

        spec, base = self._decomposition_spec()
        if base is None:
            # Nothing is decomposed yet, so the column in force is the active one.
            base = app_state.last_group_col
        columns = {str(base)} if base else set()
        if parent is not None:
            path = self._path_of_label(parent)
            for depth in range(1, len(path) + 1):
                column = spec.get(path_key(path[:depth]))
                if column:
                    columns.add(str(column))
        return columns

    def _choose_decomposition(self, parent) -> bool:
        """Ask which column refines *parent* in a window, then apply it."""
        from .legend_decompose_dialog import LegendDecomposeDialog

        columns = self._decomposition_columns()
        if not columns:
            QMessageBox.warning(
                self, translate("Warning"), translate("Please load data first.")
            )
            return False
        dialog = LegendDecomposeDialog(
            self,
            columns,
            used=self._used_decomposition_columns(parent),
            group_label=str(parent),
        )
        if dialog.exec_() != dialog.Accepted:
            return False
        column = dialog.selected_column()
        if column is None:
            return False
        return self.decompose_group_by(parent, column)

    def _create_parent_group(self):
        from PyQt5.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            translate("New Parent Group"),
            translate("Parent Group Name"),
        )
        if not ok:
            return
        name = str(name or "").strip()
        if not name:
            return
        parents = self._current_parent_groups()
        if name in parents:
            logger.info("Parent group already exists: %s", name)
            return
        parents[name] = []
        state_gateway.set_parent_groups(parents)
        self._reload_legend_panel()

    def _create_child_parent_group(self, container):
        """Create a parent group nested directly under *container*."""
        from PyQt5.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            translate("New Child Parent Group..."),
            translate("Parent Group Name"),
        )
        if not ok:
            return
        name = str(name or "").strip()
        if not name:
            return
        parents = self._current_parent_groups()
        if name in parents:
            logger.info("Parent group already exists: %s", name)
            QMessageBox.information(
                self,
                translate("New Parent Group"),
                translate("Parent group '{name}' already exists.").format(name=name),
            )
            return
        parents[name] = []
        parents.setdefault(container, []).append(name)
        state_gateway.set_parent_groups(parents)
        self._reload_legend_panel()

    def _delete_parent_group(self, parent):
        parents = self._current_parent_groups()
        if parent not in parents:
            return
        children = list(parents.pop(parent))
        # Children (groups or nested parents) move up one level: into the
        # deleted parent's own container, or to the top level.
        container = None
        for name, children_list in parents.items():
            if parent in children_list:
                container = name
                children_list.remove(parent)
                break
        if container is not None:
            target = parents.setdefault(container, [])
            for child in children:
                if child not in target:
                    target.append(child)
        state_gateway.set_parent_groups(parents)
        self._reload_legend_panel()

    def _add_group_to_parent(self, group, parent):
        parents = self._current_parent_groups()
        # A group can belong to only one parent.
        for children in parents.values():
            if group in children:
                children.remove(group)
        children = parents.setdefault(parent, [])
        if group not in children:
            children.append(group)
        state_gateway.set_parent_groups(parents)

    def _remove_group_from_parent(self, group):
        parents = self._current_parent_groups()
        changed = False
        for children in parents.values():
            if group in children:
                children.remove(group)
                changed = True
        if changed:
            state_gateway.set_parent_groups(parents)
            self._reload_legend_panel()

    def _add_parent_legend_item(self, parent, depth: int = 0):
        """Render a parent-group row: shape swatch, bold header, delete."""
        from visualization.plotting.grouping import parent_children, parent_shape

        children = parent_children(app_state, parent)
        item_widget = QWidget()
        item_layout = QHBoxLayout()
        # Nested parents are indented by their nesting level.
        item_layout.setContentsMargins(4 + 24 * max(0, depth), 2, 4, 2)
        item_layout.setSpacing(6)

        # Shape swatch: shows the shape shared by all children of this
        # parent; clicking opens the shape picker (manual override).
        shape_btn = QPushButton()
        shape_btn.setFixedSize(22, 22)
        self._update_parent_swatch(parent, shape_btn)
        shape_btn.setCursor(QCursor(Qt.PointingHandCursor))
        shape_btn.setToolTip(translate("Parent shape (shared by subgroups)"))
        shape_btn.clicked.connect(
            lambda checked=False, p=parent, btn=shape_btn: self._show_parent_shape_menu(p, btn)
        )
        item_layout.addWidget(shape_btn)

        label = QLabel(f"{translate('Parent')}: {parent}")
        label.setProperty("keepStyle", True)  # survive _NativeStyleFilter
        label.setStyleSheet("font-weight: bold;")
        item_layout.addWidget(label, 1)

        count_label = QLabel(f"({len(children)})")
        count_label.setProperty("keepStyle", True)  # survive _NativeStyleFilter
        count_label.setStyleSheet("color: #64748b;")
        item_layout.addWidget(count_label)

        # Eject button: only for parents nested inside another parent.
        from visualization.plotting.grouping import parent_of_group

        if parent_of_group(app_state, parent) is not None:
            eject_btn = QPushButton("⇱")
            eject_btn.setFixedSize(20, 20)
            eject_btn.setToolTip(translate("Remove from Parent Group"))
            eject_btn.clicked.connect(
                lambda checked=False, p=parent: self._remove_group_from_parent(p)
            )
            item_layout.addWidget(eject_btn)

        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(20, 20)
        delete_btn.setToolTip(translate("Delete Parent Group"))
        delete_btn.clicked.connect(lambda checked=False, p=parent: self._delete_parent_group(p))
        item_layout.addWidget(delete_btn)

        item_widget.setLayout(item_layout)

        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        self._set_legend_item_meta(item, "parent", parent)
        # Draggable (reorder the whole parent block's stacking) and a drop
        # target for group rows.
        item.setFlags(
            Qt.ItemIsEnabled
            | Qt.ItemIsSelectable
            | Qt.ItemIsDragEnabled
            | Qt.ItemIsDropEnabled
        )
        self._legend_list.addItem(item)
        self._legend_list.setItemWidget(item, item_widget)
