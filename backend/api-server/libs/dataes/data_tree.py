from typing import List, Dict, Any, Optional


class Tree:
    def __init__(self, data, sort_name='sort'):
        self.data = data
        self.nodes = {}
        self.roots = []
        self.sort_name = sort_name

    def _add_child(self, parent_id, child_node):
        if parent_id not in self.nodes:
            return
        self.nodes[parent_id]['children'].append(child_node)

    def _sort_children(self, node):
        node['children'].sort(key=lambda x: x[self.sort_name])
        for child in node['children']:
            self._sort_children(child)

    def build_tree(self):
        for item in self.data:
            self.nodes[item['id']] = {**item, 'children': []}
        for item in self.data:
            node_id = item['id']
            parent_id = item['pid']
            node = self.nodes[node_id]
            if parent_id == 0:
                self.roots.append(node)
            else:
                self._add_child(parent_id, node)
        self.roots.sort(key=lambda x: x[self.sort_name])

    def sort_tree(self):
        for root in self.roots:
            self._sort_children(root)

    def get_map(self):
        for root in self.roots:
            root['children'] = []
            for child in root['children']:
                root['children'].append(child)
        return self.roots

    def get_tree(self):
        """Return the tree structure as a list of dictionaries."""
        self.sort_tree()
        return self.roots

    def print_tree(self):
        """Print the tree structure as JSON."""
        import json
        self.sort_tree()
        print(json.dumps(self.get_tree(), ensure_ascii=False, indent=4))


class TreeHelper:
    def __init__(
            self,
            data: List[Dict[str, Any]],
            pid_field: str = "pid",
            id_field: str = "id",
            root_pid_value: Any = 0,
            children_field: str = "children"
    ):
        """
        初始化工具类
        :param data: 扁平化的列表数据
        :param pid_field: 父节点字段名
        :param id_field: 节点 ID 字段名
        :param root_pid_value: 根节点的 pid 值
        :param children_field: 子节点存储字段名
        """
        self.data = data
        self.pid_field = pid_field
        self.id_field = id_field
        self.root_pid_value = root_pid_value
        self.children_field = children_field

    def get_parent_node(self, node_id, data=None):
        """
        根据任意node ID获取最顶node
        :param node_id:
        :param data:
        :return: {}
        """
        if data is None:
            data = self.data
        node = next((item for item in data if item[self.id_field] == node_id), {})
        if node:
            if node[self.pid_field] == self.root_pid_value:
                return node
            else:
                self.get_parent_node(node[self.pid_field])
        else:
            return None

    def build_tree(self, data=None, sort_keys: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        构建树结构，每一层支持单独排序
        :param data: list数据
        :param sort_keys: 每层的排序字段列表（按层级顺序提供字段名）
        :return: 树形结构
        """
        if sort_keys is None:
            sort_keys = ['sort']
        if data is None:
            data = self.data

        def find_children(parent_id: Any, level: int) -> List[Dict[str, Any]]:
            children = [
                item for item in data if item.get(self.pid_field) == parent_id
            ]
            # 当前层级的排序字段
            sort_key = sort_keys[level] if level < len(sort_keys) else None
            if sort_key:
                children.sort(key=lambda x: x.get(sort_key, 0))
            # 递归查找每个子节点的子节点
            for child in children:
                child[self.children_field] = find_children(child[self.id_field], level + 1)
            return children

        # 从根节点开始构建树
        return find_children(self.root_pid_value, 0)

    def get_tree_by_name(self, data=None, name=None):

        if name is None:
            return self.build_tree()
        res = []
        if data is None:
            data = self.build_tree()
        parent_nodes = []
        data_map = {}
        for item in data:
            print(1111, item['name'],name)
            data_map[item[self.id_field]] = item
            if name in item.get('name', ''):
                parent_node = self.get_parent_node(item[self.pid_field], data)
                parent_nodes.append(parent_node.get(self.id_field))

        parent_nodes = list(set(parent_nodes))

        for n in parent_nodes:
            if n  in data_map:
                res.append(data_map[n])
        return res

    def filter_tree_by_node(self, node_id: Any, sort_keys: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        根据指定节点 ID 获取该节点及其子节点组成的树
        :param node_id: 节点 ID
        :param sort_keys: 每层的排序字段列表（按层级顺序提供字段名）
        :return: 指定节点的子树，或 None 如果节点不存在
        """
        if sort_keys is None:
            sort_keys = []

        # 查找节点
        def find_node_and_children(node_id: Any, level: int) -> Optional[Dict[str, Any]]:
            for item in self.data:
                if item.get(self.id_field) == node_id:
                    # 找到节点后递归查找其子节点
                    children = [child for child in self.data if child.get(self.pid_field) == node_id]
                    # 当前层级的排序字段
                    sort_key = sort_keys[level] if level < len(sort_keys) else None
                    if sort_key:
                        children.sort(key=lambda x: x.get(sort_key, 0))
                    # 递归处理子节点
                    for child in children:
                        child[self.children_field] = find_node_and_children(child[self.id_field], level + 1)[
                            self.children_field
                        ]
                    item[self.children_field] = children
                    return item
            return None

        return find_node_and_children(node_id, 0)

    def get_tree_by_depth(self, tree: List[Dict[str, Any]], depth: int) -> List[Dict[str, Any]]:
        """
        根据层数限制树形数据
        :param tree: 树形结构数据
        :param depth: 树的最大层数
        :return: 限制深度后的树形结构
        """
        if depth <= 0:
            return []

        def prune(node: Dict[str, Any], current_depth: int) -> Dict[str, Any]:
            if current_depth >= depth:
                node.pop(self.children_field, None)
            else:
                node[self.children_field] = [
                    prune(child, current_depth + 1) for child in node.get(self.children_field, [])
                ]
            return node

        return [prune(node, 1) for node in tree]

    def get_ancestors_by_node_id(self, node_id: Any) -> List[Dict[str, Any]]:
        """
        根据子节点 ID 获取该节点之上的树形数据（包括父节点）
        :param node_id: 子节点 ID
        :return: 该节点及其所有父节点的列表
        """
        # 构建一个以 ID 为键的字典，方便查找
        id_map = {item[self.id_field]: item for item in self.data}
        # 定义一个列表来保存结果
        ancestors = []
        # 从节点开始向上查找父节点
        current_node_id = node_id
        while current_node_id in id_map:
            current_node = id_map[current_node_id]
            ancestors.append(current_node)
            current_node_id = current_node.get(self.pid_field)  # 更新为父节点 ID
        # 反转列表以从根节点到当前节点
        return ancestors[::-1]

    def get_node_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据子节点名称模糊查询获取该节点
        :param name: 子节点名称
        :return: 匹配的节点，或 None 如果没有找到
        """
        for item in self.data:
            if name in item.get('name', ''):  # 假设节点名称存储在 'name' 字段
                return item
        return None

    def get_ancestors_by_name(self, name: str = None) -> List[Dict[str, Any]]:
        """
        根据子节点名称模糊查询获取该节点之上的树形数据（包括父节点）
        :param name: 子节点名称
        :return: 该节点及其所有父节点的列表
        """
        if name == "" or name is None:
            return self.build_tree()
        node = self.get_node_by_name(name)
        if not node:
            return []  # 如果没有找到节点，返回空列表

        # 从节点开始向上查找父节点
        ancestors = []
        current_node_id = node[self.id_field]

        # 构建一个以 ID 为键的字典，方便查找父节点
        id_map = {item[self.id_field]: item for item in self.data}

        while current_node_id in id_map:
            current_node = id_map[current_node_id]
            ancestors.append(current_node)
            current_node_id = current_node.get(self.pid_field)  # 更新为父节点 ID

        # 反转列表以从根节点到当前节点
        ancestors = ancestors[::-1]
        result_tree = self.build_tree_structure(ancestors)
        return result_tree

    def build_tree_structure(self, ancestors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据找到的祖先节点构建树形结构
        :param ancestors: 祖先节点列表
        :return: 构建的树形结构
        """
        if not ancestors:
            return []

        # 初始化树形结构
        root = ancestors[0]  # 根节点
        tree_structure = {root[self.id_field]: {**root, self.children_field: []}}

        for ancestor in ancestors[1:]:
            current_id = ancestor[self.id_field]
            parent_id = ancestor[self.pid_field]

            # 找到父节点并添加到其子节点中
            if parent_id in tree_structure:
                tree_structure[parent_id][self.children_field].append(ancestor)

        return list(tree_structure.values())

    def get_branch_by_name(self, name: str = None) -> List[Dict[str, Any]]:
        """
        根据子节点名称模糊查询获取该节点所在枝干上的所有节点
        :param name: 子节点名称
        :return: 该节点所在枝干的所有节点
        """
        if name == "" or name is None:
            return self.build_tree()
        # 查找所有匹配的节点
        matched_nodes = [item for item in self.data if name in item.get('name', '')]
        if not matched_nodes:
            return []  # 如果未找到节点，返回空列表

        all_branch_nodes = []
        for node in matched_nodes:
            # 获取当前节点及其所有父节点
            current_node_id = node[self.id_field]
            branch = []

            # 向上查找父节点
            while True:
                current_node = next((item for item in self.data if item[self.id_field] == current_node_id), None)
                if current_node is None:
                    break
                branch.append(current_node)
                current_node_id = current_node.get(self.pid_field)  # 更新为父节点 ID

            # 反转列表以从根节点到当前节点
            branch = branch[::-1]
            current_node_children = [item for item in self.data if item[self.pid_field] == node[self.id_field]]
            node[self.children_field] = current_node_children  # 将子节点添加到当前节点中
            branch.append(node)  # 添加当前节点

            # 将子节点添加到枝干上
            branch.extend(current_node_children)
            all_branch_nodes.extend(branch)

        return all_branch_nodes


def get_menu_tree(data):
    tree = TreeHelper(data)
    return tree.build_tree(sort_keys=['sort'])


def get_tree_filter(data, name=None):
    tree = TreeHelper(data)
    return tree.build_tree()


def get_map(data):
    tree = Tree(data)
    tree.build_tree()
    return tree.get_tree()
