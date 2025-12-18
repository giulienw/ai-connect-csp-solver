import sys
import json
import tempfile
from pathlib import Path
from run import format_solution, reformat_to_grid, main, write_results_csv

def build_demo_solution(puzzle):
    return {
        "House_1_Color": "Red",
        "House_1_Pet": "Dog",
        "House_2_Color": "Blue",
        "House_2_Pet": "Cat"
    }

def test_format_solution_solved(monkeypatch):
    solution = {"House_1_Color": "Red"}
    grid = format_solution(solution)
    assert grid["status"] == "solved"
    assert "header" in grid and "rows" in grid

def test_format_solution_unsolved():
    grid = format_solution({})
    assert grid["status"] == "unsolved"
    assert grid["header"] == []
    assert grid["rows"] == []

def test_reformat_to_grid_basic():
    assignment = {"House_1_Color": "Red", "House_2_Color": "Blue"}
    grid = reformat_to_grid(assignment)
    assert grid["header"] == ["House", "Color"]
    assert len(grid["rows"]) == 2
    assert grid["rows"][0][1] == "Red"

def test_main_single_file(monkeypatch):
    monkeypatch.setattr("run.solve_puzzle", build_demo_solution)

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmpfile:
        json.dump({"id": "puzzle1"}, tmpfile)
        tmpfile_path = Path(tmpfile.name)

    sys.argv = ["run.py", str(tmpfile_path)]

    main()

    tmpfile_path.unlink()

def test_main_directory_input(monkeypatch):
    monkeypatch.setattr("run.solve_puzzle", build_demo_solution)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        for i in range(3):
            f = tmpdir_path / f"puzzle{i}.json"
            f.write_text(json.dumps({"id": f"puzzle{i}"}))

        sys.argv = ["run.py", str(tmpdir_path)]
        main()

def test_main_malformed_json(monkeypatch):
    monkeypatch.setattr("run.solve_puzzle", build_demo_solution)
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmpfile:
        tmpfile.write("{invalid json")
        tmpfile_path = Path(tmpfile.name)

    sys.argv = ["run.py", str(tmpfile_path)]
    main()
    tmpfile_path.unlink()

def test_csv_output(monkeypatch):
    monkeypatch.setattr("run.solve_puzzle", build_demo_solution)
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmpfile:
        tmpfile.write(json.dumps({"id": "puzzle_csv"}))
        tmpfile_path = Path(tmpfile.name)

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False) as csvfile:
        output_path = Path(csvfile.name)

    sys.argv = ["run.py", str(tmpfile_path), "--output", str(output_path)]
    main()

    content = output_path.read_text()
    assert "id,grid_solution,steps" in content
    assert "puzzle_csv" in content

    tmpfile_path.unlink()
    output_path.unlink()
