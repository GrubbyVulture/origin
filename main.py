import os
from collections import defaultdict, deque
import re

class Parser:
    PATH = "C:\\Users\\曾子泰\\Desktop\\testcode2.txt"  # 文法文件路径
    START = None  # 开始符号
    VN, VT = set(), set()  # 非终结符号集和终结符号集
    MAP = defaultdict(list)  # key:产生式左边 value:产生式右边(含多条)
    oneLeftFirst = {}  # 用于构建预测分析表的FIRST集合
    FIRST, FOLLOW = defaultdict(set), defaultdict(set)  # FIRST和FOLLOW集合
    FORM = []  # 预测分析表
    preMap = {}  # 预测分析表的映射

    @classmethod
    def main(cls):
        cls.init()
        cls.identifyVnVt(cls.read_file(cls.PATH))
        cls.reform_map()
        cls.find_first()
        cls.find_follow()
        cls.pre_form()
        print("请输入要分析的单词串:")
        input_str = input().strip()
        cls.print_auto_pre(input_str)

    # 初始化变量
    @classmethod
    def init(cls):
        cls.VN.clear()
        cls.VT.clear()
        cls.MAP.clear()
        cls.FIRST.clear()
        cls.FOLLOW.clear()
        cls.oneLeftFirst.clear()
        cls.preMap.clear()

    # 从文件中读取文法
    @classmethod
    def read_file(cls, path):
        print("从文件读入的文法为:")
        result = []
        try:
            with open(path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line:
                        print(f"\t{line}")
                        result.append(line)
        except Exception as e:
            print(f"读取文件时出错: {e}")
        return result

    # 符号分类
    @classmethod
    def identifyVnVt(cls, rules):
        cls.START = rules[0][0]  # 第一行的第一个字符为开始符号

        for rule in rules:
            left, right = map(str.strip, rule.split("→"))
            cls.VN.add(left)

            right_variants = []
            for symbol in right.split('|'):
                symbol = symbol.strip()
                symbols = []
                i = 0
                while i < len(symbol):
                    # 处理单引号情况
                    if i + 1 < len(symbol) and (symbol[i + 1] == '\'' or symbol[i + 1] == '’'):
                        symbols.append(symbol[i:i + 2])
                        i += 2
                    else:
                        symbols.append(symbol[i])
                        i += 1
                right_variants.append(symbols)
                cls.VT.update(symbols)
            cls.MAP[left].extend(right_variants)

        # 从终结字符集去掉非终结符
        cls.VT -= cls.VN
        print("\nVn集合:\t{" + "、".join(cls.VN) + "}")
        print("Vt集合:\t{" + "、".join(cls.VT) + "}")

    # 消除直接左递归并提取左公因子
    @classmethod
    def reform_map(cls):
        is_reformed = False
        null_sign = ["ε"]
        keys = list(cls.MAP.keys())

        for left in keys:
            right_list = cls.MAP[left]
            old_rights = []  # 保存不含左递归的右部
            new_rights = []  # 保存含左递归的右部

            for production in right_list:
                if production[0] == left:  # 检查左递归
                    new_rights.append(production[1:] + [left + "'"])  # 新产生式
                else:
                    old_rights.append(production + [left + "'"])  # 原产生式

            if new_rights:  # 存在左递归
                is_reformed = True
                cls.MAP[left] = old_rights
                new_rights.append(null_sign)  # 添加空产生式
                cls.MAP[left + "'"] = new_rights
                cls.VN.add(left + "'")
                cls.VT.add("ε")  # 将空符号加入终结符集

        if is_reformed:
            print("消除文法的左递归:")
            for k, v in cls.MAP.items():
                print(f"\t{k} → {' | '.join(''.join(p) for p in v)}")

    # 计算每个非终结符的 FIRST 集合
    @classmethod
    def find_first(cls):
        print("\nFIRST集合:")
        for key in cls.VN:
            cls._compute_first(key)
        # 输出 FIRST 集合
        for key, first_set in cls.FIRST.items():
            print(f"\tFIRST({key}) = {{ {', '.join(first_set)} }}")

    # 递归计算 FIRST 集合的辅助方法
    @classmethod
    def _compute_first(cls, symbol):
        if symbol in cls.FIRST:
            return cls.FIRST[symbol]

        first_set = set()
        if symbol in cls.VT:
            first_set.add(symbol)
        else:
            for production in cls.MAP[symbol]:
                for s in production:
                    if s == symbol:  # 避免无限递归
                        break
                    result = cls._compute_first(s)
                    first_set.update(result - {"ε"})
                    if "ε" not in result:
                        break
                else:
                    first_set.add("ε")  # 如果所有符号都能推出 ε，则添加 ε

        cls.FIRST[symbol] = first_set
        return first_set

    # 计算每个非终结符的 FOLLOW 集合
    @classmethod
    def find_follow(cls):
        print("\nFOLLOW集合:")
        cls.FOLLOW[cls.START].add("#")  # 开始符号的 FOLLOW 集合包含结束符号 '#'

        while True:
            updated = False
            for left, productions in cls.MAP.items():
                for production in productions:
                    follow_temp = cls.FOLLOW[left]
                    for i in reversed(range(len(production))):
                        symbol = production[i]
                        if symbol in cls.VN:
                            if follow_temp - cls.FOLLOW[symbol]:
                                cls.FOLLOW[symbol].update(follow_temp)
                                updated = True
                            if "ε" in cls.FIRST[production[i]]:
                                follow_temp = follow_temp.union(cls.FIRST[production[i]] - {"ε"})
                            else:
                                follow_temp = cls.FIRST[production[i]]
                        else:
                            follow_temp = {symbol}
            if not updated:
                break

        # 输出 FOLLOW 集合
        for key, follow_set in cls.FOLLOW.items():
            print(f"\tFOLLOW({key}) = {{ {', '.join(follow_set)} }}")

    # 构建预测分析表 FORM
    @classmethod
    def pre_form(cls):
        vt_set = cls.VT - {"ε"}  # 去除空符号 'ε'
        vt_list = sorted(vt_set) + ["#"]  # 将终结符按字母排序，并添加结束符号 '#'
        vn_list = sorted(cls.VN)  # 将非终结符按字母排序
        cls.FORM = [[None] * (len(vt_list) + 1) for _ in range(len(vn_list) + 1)]

        # 表头设置
        cls.FORM[0][1:] = vt_list
        for i, vn in enumerate(vn_list, start=1):
            cls.FORM[i][0] = vn

        # 填充表格
        for vn in vn_list:
            row = vn_list.index(vn) + 1
            for production in cls.MAP[vn]:
                first_set = cls._compute_first_sequence(production)
                for terminal in first_set:
                    if terminal != "ε":
                        col = vt_list.index(terminal) + 1
                        cls.FORM[row][col] = f"{vn}→{''.join(production)}"
                # 若包含空符号 'ε'，则根据 FOLLOW 集合进行填写
                if "ε" in first_set:
                    for follow_symbol in cls.FOLLOW[vn]:
                        col = vt_list.index(follow_symbol) + 1
                        cls.FORM[row][col] = f"{vn}→ε"

        # 打印预测分析表
        print("\n该文法的预测分析表为：")
        header = "\t".join([" "] + vt_list)
        print(header)
        for row in cls.FORM:
            row_str = "\t".join(symbol if symbol else " " for symbol in row)
            print(row_str)

    # 计算一个产生式序列的 FIRST 集合
    @classmethod
    def _compute_first_sequence(cls, sequence):
        result = set()
        for symbol in sequence:
            symbol_first = cls.FIRST.get(symbol, {symbol})
            result.update(symbol_first - {"ε"})
            if "ε" not in symbol_first:
                break
        else:
            result.add("ε")  # 如果序列中所有符号都能产生 ε
        return result

    # 分析输入的单词串并输出推导过程
    @classmethod
    def print_auto_pre(cls, input_str):
        print(f"{input_str} 的分析过程:")
        queue = deque(input_str + "#")  # 将输入串和结束符号 '#' 入队
        stack = ["#", cls.START]  # 初始化分析栈，包含结束符号和起始符号
        step = 1

        while stack:
            stack_top = stack[-1]
            queue_front = queue[0]

            # (1)分析成功
            if stack_top == queue_front == "#":
                print(f"{step}\t{''.join(stack)}\t{''.join(queue)}\t分析成功")
                break

            # (2)匹配终结符
            if stack_top == queue_front:
                stack.pop()
                queue.popleft()
                print(f"{step}\t{''.join(stack)}\t{''.join(queue)}\t匹配 {stack_top}")
                step += 1
                continue

            # (3)查表获取产生式
            row = next((i for i, vn in enumerate(cls.FORM) if vn[0] == stack_top), None)
            col = next((j for j, vt in enumerate(cls.FORM[0]) if vt == queue_front), None)

            if row is not None and col is not None and cls.FORM[row][col]:
                production = cls.FORM[row][col].split("→")[1]
                stack.pop()
                if production != "ε":
                    stack.extend(reversed(production))
                print(f"{step}\t{''.join(stack)}\t{''.join(queue)}\t用 {cls.FORM[row][col]}")
                step += 1
            else:
                print(f"{step}\t{''.join(stack)}\t{''.join(queue)}\t分析失败")
                break

if __name__ == "__main__":
    Parser.main()
    print("读取完成")

