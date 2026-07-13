import re
from io import BytesIO
from zipfile import ZipFile, BadZipFile
from dataclasses import dataclass
from fastapi import status, HTTPException, UploadFile
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.testCase import TestCaseCreate, TestCaseUpdate
from app.models import TestCase, Task

async def create_test_case(testInfo: TestCaseCreate, db: AsyncSession) -> TestCase:
    task = await db.get(Task, testInfo.task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    last_order = (await db.execute(
        select(func.max(TestCase.order))
            .where(TestCase.task_id == testInfo.task_id)
    )).scalar()

    order = 1 if last_order is None else last_order + 1

    new_test_case = TestCase(
        task_id = testInfo.task_id,
        input = testInfo.input,
        expected_output = testInfo.expected_output,
        is_hidden = testInfo.is_hidden,
        order = order
    )

    db.add(new_test_case)

    try:
        await db.commit()
        await db.refresh(new_test_case)
        return new_test_case
    except Exception:
        await db.rollback()
        raise


async def get_test_case(test_case_id: int, db: AsyncSession) -> TestCase:
    test_case = await db.get(TestCase, test_case_id)
    if not test_case or test_case.is_hidden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    return test_case


async def get_test_cases_by_task(task_id: int, db: AsyncSession) -> list[TestCase]:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    result = await db.execute(
        select(TestCase)
            .where(TestCase.task_id == task_id)
            .order_by(TestCase.order)
    )
    
    return result.scalars().all() 


async def update_test_case(test_case_id: int, test_case_update: TestCaseUpdate, db: AsyncSession) -> TestCase:
    test_case = await db.get(TestCase, test_case_id)
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test Case not found"
        )
    
    data = test_case_update.model_dump(exclude_unset=True)
    if not data:
        return test_case
    for key, val in data.items():
        setattr(test_case, key, val)
    
    try:
        await db.commit()
        await db.refresh(test_case)
        return test_case
    except Exception:
        await db.rollback()
        raise


async def delete_test_case(test_case_id: int, db: AsyncSession):
    test_case = await db.get(TestCase, test_case_id)
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test Case not found"
        )
    
    try:
        await db.delete(test_case)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

# --------------------- ZIP FILE PROCESSING -------------------------------

INPUT_PATTERN = re.compile(r'^input(\d+)\.txt$')
OUTPUT_PATTERN = re.compile(r'^output(\d+)\.txt$')


@dataclass
class PairNames:
    input: str | None
    output: str | None


async def _open_zip(file: UploadFile) -> ZipFile:
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a .zip file"
        )
    content = await file.read()
    try:
        archive = ZipFile(BytesIO(content))
        return archive
    except BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid zip file"
        )


def _get_pairs(archive: ZipFile) -> list[PairNames]:
    def _handle_name(name: str, match: re.Match[str]):
        other = 'input' if name == 'output' else 'output'
        number = int(match.group(1))
        if number in pairs and getattr(pairs[number], name) is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate {name} file for test case {number}"
            )
        elif number in pairs:
            setattr(pairs[number], name, match.group(0))
        else:
            params = {name: match.group(0), other: None}
            pairs[number] = PairNames(**params)

    pairs: dict[int, PairNames] = {}
    names = archive.namelist()
    for name in names:
        if name.endswith('/'):
            continue
        elif input_m := INPUT_PATTERN.match(name):
            _handle_name(name='input', match=input_m)
        elif output_m := OUTPUT_PATTERN.match(name):
            _handle_name(name='output', match=output_m)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file name in zip: {name}. Expected inputN.txt or outputN.txt"
            )
    if not pairs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid test case files found in the zip"
        )
    for number, pair in pairs.items():
        if pair.input is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing input file for test case {number}"
            )
        elif pair.output is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing output file for test case {number}"
            )
    return [p for _, p in sorted(pairs.items())]
    

def _read_text(archive: ZipFile, filename: str) -> str:
    try:
        with archive.open(filename) as f:
            return f.read().decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All test files must be UTF-8 encoded."
        )
    

async def import_tests_zip(task_id: int, file: UploadFile, db: AsyncSession):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    archive = await _open_zip(file=file)
    with archive:
        lstPairs = _get_pairs(archive=archive)
        tests = []
        try:
            await db.execute(
                delete(TestCase)
                    .where(TestCase.task_id == task_id)
            )
            for order, pair in enumerate(lstPairs, start=1):
                input_data = _read_text(archive=archive, filename=pair.input)
                output_data = _read_text(archive=archive, filename=pair.output)
                
                new_test_case = TestCase(
                    task_id=task_id,
                    input=input_data,
                    expected_output=output_data,
                    is_hidden=True,
                    order=order
                )
                tests.append(new_test_case)
            
            db.add_all(tests)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
