# %%
# SMVVの反例から変数の変化をテーブルに変換するスクリプト
import re
import sys
import pandas as pd
import argparse

# %%
COUNTEREXAMPLE = """
*** This is NuSMV 2.7.0 (compiled on Thu Oct 24 17:56:00 2024)
*** Enabled addons are: compass
*** For more information on NuSMV see <http://nusmv.fbk.eu>
*** or email to <nusmv-users@list.fbk.eu>.
*** Please report bugs to <Please report bugs to <nusmv-users@fbk.eu>>

*** Copyright (c) 2010-2024, Fondazione Bruno Kessler

*** This version of NuSMV is linked to the CUDD library version 2.4.1
*** Copyright (c) 1995-2004, Regents of the University of Colorado

*** This version of NuSMV is linked to the MiniSat SAT solver.
*** See http://minisat.se/MiniSat.html
*** Copyright (c) 2003-2006, Niklas Een, Niklas Sorensson
*** Copyright (c) 2007-2010, Niklas Sorensson

-- specification AG !(!is_lid_closed & heater_on)  is false
-- as demonstrated by the following execution sequence
Trace Description: CTL Counterexample
Trace Type: Counterexample
  -> State: 1.1 <-
    status = Idle
    water_level = 0
    temperature = Cold
    is_lid_closed = FALSE
    is_locked = FALSE
    heater_on = FALSE
    boil_timer = 0
    boil_button_pressed = FALSE
    unlock_button_pressed = FALSE
    dispense_button_pressed = FALSE
  -> State: 1.2 <-
    water_level = 3
    temperature = Warm
    is_lid_closed = TRUE
    is_locked = TRUE
  -> State: 1.3 <-
    status = Boiling
    temperature = BoilingTemp
    boil_timer = 1
  -> State: 1.4 <-
    water_level = 0
    temperature = Cold
    is_lid_closed = FALSE
    is_locked = FALSE
    heater_on = TRUE
    boil_timer = 0
-- specification AG ((((status = Idle & boil_button_pressed) & is_lid_closed) & water_level > 0) -> AF status = Boiling)  is false
-- as demonstrated by the following execution sequence
Trace Description: CTL Counterexample
Trace Type: Counterexample
  -> State: 2.1 <-
    status = Idle
    water_level = 0
    temperature = Cold
    is_lid_closed = FALSE
    is_locked = FALSE
    heater_on = FALSE
    boil_timer = 0
    boil_button_pressed = FALSE
    unlock_button_pressed = FALSE
    dispense_button_pressed = FALSE
  -- Loop starts here
  -> State: 2.2 <-
    water_level = 3
    temperature = Warm
    is_lid_closed = TRUE
    boil_button_pressed = TRUE
    dispense_button_pressed = TRUE
  -> State: 2.3 <-
    status = Dispensing
    boil_button_pressed = FALSE
    dispense_button_pressed = FALSE
  -> State: 2.4 <-
    status = Idle
    boil_button_pressed = TRUE
    dispense_button_pressed = TRUE
"""

# %%
pattern = r"""
    ^\s*           # 行頭の空白
    ->             # Stateの開始を示す
    \s+
    State:
    \s+
    (\d+)\.(\d+)   # ステート番号（例: 1.1, 2.3など）
    \s+
    <-             # ステートの終了を示す
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
    temp_loop = False
    example_num = 0
    step_num = 0
    temp_example_num = 0
    temp_step_num = 0
    for line in counter_example.splitlines():
        line = line.strip()

        # ループの開始を検出
        # ループは次のStateから開始されるため、テーブル出力にはまだ反映しない
        if "-- Loop starts here" in line:
            temp_loop = True

        m = re.match(pattern, line, re.VERBOSE)
        if m:
            # State更新前に1つ前のStateを出力
            if example_num != 0:
                data.append(
                    {
                        "example": example_num,
                        "step": step_num,
                        "loop": loop,
                        **variables,  # 変数の値を展開
                    }
                )

            temp_example_num, temp_step_num = m.groups()
            # exampleが変わったらリセット
            if temp_example_num != example_num:
                loop = False
                temp_loop = False
            example_num = temp_example_num
            step_num = temp_step_num
            loop = temp_loop
        elif "--" not in line and "=" in line:
            # 変数の更新行を検出
            variable, value = line.split("=")
            variables[variable.strip()] = value.strip()

    # 最後のState出力
    data.append(
        {
            "example": example_num,
            "step": step_num,
            "loop": loop,
            **variables,  # 変数の値を展開
        }
    )

    return pd.DataFrame(data)


# %%
def main():
    parser = argparse.ArgumentParser(
        description="Convert NuSMV counter example to PlantUML sequence diagram."
    )
    parser.add_argument(
        "-i",
        "--input_file",
        help="Path to the NuSMV counter example file. If not provided, a sample will be used.",
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
        print("e.g. python ce2seq_smv.py -i counter_example.txt")
        print("")
        print("Using sample counter example.")
        counter_example = COUNTEREXAMPLE
    else:
        with open(args.input_file, "r") as f:
            counter_example = f.read()

    variables = {}

    df = convert_to_dataframe(counter_example, variables)

    # NuSMVはfloatの型を本来もたないため、intに変換して出力
    for col in df.select_dtypes(include=["float"]):
        df[col] = df[col].astype("Int64")

    df.to_csv("variable_table.csv", index=False)


# %%
if __name__ == "__main__":
    main()

# %%
