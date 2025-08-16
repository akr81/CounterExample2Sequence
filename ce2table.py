# %%
# SPINの反例から変数の変化をテーブルに変換するスクリプト
import re
import sys
import pandas as pd
import argparse

# %%
COUNTEREXAMPLE = """
spin: main_original.pml:0, warning, proctype Agent, 'int   acked' variable is never used (other than in print stmnts)
spin: main_original.pml:0, warning, proctype DB, 'int   count' variable is never used (other than in print stmnts)
starting claim 3
MSC: ~G line 4
  1:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
Never claim moves to line 4	[(1)]
Starting Agent with pid 2
  2:	proc  0 (:init::1) main_original.pml:88 (state 1)	[(run Agent())]
Starting DB with pid 3
  3:	proc  0 (:init::1) main_original.pml:89 (state 2)	[(run DB())]
  4:	proc  0 (:init::1) main_original.pml:90 (state 3)	[Agent_ch!request_send]
  5:	proc  1 (Agent:1) main_original.pml:20 (state 1)	[Agent_ch?event]
  6:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
  7:	proc  2 (DB:1) main_original.pml:80 (state 33)	[(1)]
  8:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
  9:	proc  2 (DB:1) main_original.pml:81 (state 34)	[DB_state = stop]
 10:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
 11:	proc  2 (DB:1) main_original.pml:77 (state 31)	[((DB_state==stop))]
 12:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
 13:	proc  1 (Agent:1) main_original.pml:22 (state 2)	[(((Agent_state==ready)&&(event==request_send)))]
 14:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
 15:	proc  2 (DB:1) main_original.pml:78 (state 32)	[DB_state = ready]
 16:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
 17:	proc  1 (Agent:1) main_original.pml:23 (state 3)	[DB_ch!send_data]
 18:	proc  2 (DB:1) main_original.pml:44 (state 1)	[DB_ch?event]
 19:	proc  - (spec1:1) _spin_nvr.tmp:4 (state 4)	[(1)]
 20:	proc  1 (Agent:1) main_original.pml:24 (state 4)	[Agent_state = sending]
MSC: ~G line 3
 21:	proc  - (spec1:1) _spin_nvr.tmp:3 (state 1)	[(!((!((Agent_state==sending))||(78==ready))))]
Never claim moves to line 3	[(!((!((Agent_state==sending))||(78==ready))))]
spin: _spin_nvr.tmp:3, Error: assertion violated
spin: text of failed assertion: assert(!(!((!((Agent_state==sending))||(78==ready)))))
#processes: 3
 22:	proc  2 (DB:1) main_original.pml:45 (state 20)
 22:	proc  1 (Agent:1) main_original.pml:19 (state 14)
 22:	proc  0 (:init::1) main_original.pml:92 (state 5)
 22:	proc  - (spec1:1) _spin_nvr.tmp:3 (state 2)
3 processes created
Exit-Status 0

"""

# %%
pattern = r"""
    ^\s*           # 行頭の空白
    (\d+)          # step番号
    :\s*proc\s*    # プロセス
    \d+\s*         # プロセス番号を読み飛ばす
    \(
        ([^)]+)    # プロセス名
    \)\s+
    ([^\s]+:\d+)   # ファイル名と行番号
    \s*\(state\s*\d+\)\s*  # SPINの内部状態を読み飛ばす
    \[
        (.+?)      # 処理
    \]
    \s*$           # 行末の空白
"""


# %%
import ast, keyword


class StringifyUnknownNames(ast.NodeTransformer):
    def __init__(self, allowed_names):
        self.allowed_names = set(allowed_names) | {"True", "False", "None"}

    def visit_Name(self, node: ast.Name):
        # 右辺などの読み取り専用（Load）の名前だけを対象にする
        if isinstance(node.ctx, ast.Load):
            name = node.id
            if name not in self.allowed_names and not keyword.iskeyword(name):
                return ast.Constant(value=name)  # 未知の名前 → "name"
        return node


# %%
def initialize_globals_from_pml(pml_filepath: str) -> dict:
    """Promela (.pml) ファイルを読み込み、グローバル変数の初期値を抽出する。"""
    variables = {}
    # 正規表現パターン: "型名 変数名 = 値;" の形式にマッチ
    pattern = re.compile(r"^\s*(?:int|bool|mtype|byte)\s+(\w+)\s*=\s*([^;]+);")

    with open(pml_filepath, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.match(line)
            if m:
                var_name, var_value = m.groups()
                # 抽出した値をsmart_execで評価して辞書に格納
                # これにより 'sw = off' のようなものも正しく処理できる
                temp_env = {}
                smart_exec(f"{var_name} = {var_value}", temp_env)
                variables.update(temp_env)

    print(f".pmlファイルから初期値を読み込みました: {variables}")
    return variables


# %%

# 最低限の安全チェック（許可するノードだけ通す）
_ALLOWED_NODES = {
    ast.Module,
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,
    ast.Expr,
    ast.Name,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.IfExp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
    ast.Load,
    ast.Store,
    ast.Tuple,
    ast.List,
    ast.Dict,
    ast.Set,
    ast.Subscript,
    ast.Slice,
    ast.Index,
    ast.Attribute,
}


def _assert_safe(tree: ast.AST):
    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_NODES:
            raise ValueError(f"Disallowed syntax: {type(node).__name__}")


def smart_exec(assign_src: str, env: dict):
    """
    代入文を受け取り、環境にない単語を自動で文字列化してから exec する。
    例: smart_exec('sw = off', env) → env['sw'] == 'off'
    """
    # パース（代入文を想定）
    tree = ast.parse(assign_src, mode="exec")

    # 安全チェック
    _assert_safe(tree)

    # 未知Nameを"文字列"に変換
    transformer = StringifyUnknownNames(allowed_names=env.keys())
    tree2 = transformer.visit(tree)
    ast.fix_missing_locations(tree2)

    # 実行（globalsは空、localsにenv）
    code = compile(tree2, "<smart_exec>", "exec")
    exec(code, {}, env)
    return env


# %%
def convert_to_dataframe(counter_example: str, variables: dict = {}) -> pd.DataFrame:
    """Convert a SPIN counter example output to a DataFrame.

    Args:
        counter_example (str): Counter example output from SPIN
        variables (dict): Initialized variables from the Promela (.pml) file

    Returns:
        pd.DataFrame: DataFrame containing the parsed data
    """
    data = []
    loop = False
    for line in counter_example.splitlines():
        line = line.strip()

        # ループの開始を検出
        if "<<<<<START OF CYCLE>>>>>" in line:
            loop = True

        m = re.match(pattern, line, re.VERBOSE)
        if m:
            step_num, process_name, file_line, action = m.groups()

            # actionが値を更新する場合、変数名と値を抽出
            if "=" in action and "==" not in action:
                pass
            else:
                # 変数の更新がない場合はスキップ
                continue

            # 変数を更新する右辺の式を評価
            smart_exec(action, variables)

            data.append(
                {
                    "step": int(step_num),
                    "loop": loop,
                    "process": process_name,
                    "action": action,
                    "file_line": file_line,
                    **variables,  # 変数の値を展開
                }
            )

    return pd.DataFrame(data)


# %%
def main():
    parser = argparse.ArgumentParser(
        description="Convert SPIN counter example to PlantUML sequence diagram."
    )
    parser.add_argument(
        "-i",
        "--input_file",
        help="Path to the SPIN counter example file. If not provided, a sample will be used.",
        default=None,
    )
    parser.add_argument(
        "-p",
        "--pml_file",
        required=True,
        help="REQUIRED: Path to the Promela file.",
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output_file",
        help="Path to save the output csv file. If not provided, it will output as variable_table.csv.",
        default="variable_table.csv",
    )

    args = parser.parse_args()

    # 入力ファイルの指定がなければサンプルとしてCOUNTEREXAMPLEを使用
    if not args.input_file:
        print("Specify the path to the counter example file as an argument.")
        print("e.g. python ce2seq.py -i counter_example.txt")
        print("")
        print("Using sample counter example.")
        counter_example = COUNTEREXAMPLE
    else:
        with open(args.input_file, "r") as f:
            counter_example = f.read()

    if args.pml_file:
        variables = initialize_globals_from_pml(args.pml_file)

    df = convert_to_dataframe(counter_example, variables)

    # SPINはfloatの型を本来もたないため、intに変換して出力
    for col in df.select_dtypes(include=["float"]):
        df[col] = df[col].astype("Int64")

    df.to_csv("variable_table.csv", index=False)


# %%
if __name__ == "__main__":
    main()

# %%
