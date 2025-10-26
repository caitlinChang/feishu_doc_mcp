import requests
from typing import Optional, List
from . import config
from pydantic import BaseModel, Field

# --- Pydantic Models for Create MR Response ---

class ResponseMetadata(BaseModel):
    RequestId: str
    Action: str
    Version: str
    Service: str
    Region: str

class Commit(BaseModel):
    Id: str
    Title: str
    Message: str
    Author: dict
    Committer: dict
    Parents: List[str]
    TreeId: str

class Branch(BaseModel):
    Name: str
    Commit: Commit

class DisplayName(BaseModel):
    Content: str
    I18n: dict

class User(BaseModel):
    Id: str
    Username: str
    DisplayName: DisplayName
    Email: str
    TenantId: str
    CreatedAt: str
    Type: str
    Status: str
    AvatarURL: str
    CanPinRepository: bool
    Location: str
    ThemeMode: str
    Language: str

class Version(BaseModel):
    Id: str
    Number: int
    MergeRequestId: int
    CreatedAt: str
    SourceCommitId: str
    TargetCommitId: str
    BaseCommitId: str
    Type: str

class MergeRequest(BaseModel):
    Id: str
    Number: int
    Status: str
    SourceRepoId: str
    TargetRepoId: str
    SourceBranchName: str
    TargetBranchName: str
    SourceBranch: Branch
    TargetBranch: Branch
    Title: str
    Description: str
    CreatedBy: User
    CreatedAt: str
    UpdatedBy: User
    UpdatedAt: str
    ChangesCount: int
    CommitsCount: int
    DivergedCommitsCount: int
    Versions: List[Version]
    ChangeMode: str
    URL: str
    AutoInviteReviewers: bool
    Draft: bool
    AttentionSet: list
    MergeMethod: str
    AutoMerge: bool
    RemoveSourceBranchAfterMerge: bool
    MergeInProgress: bool
    MergeCommitMessage: str
    SquashCommitMessage: str
    MergeCommitId: str
    MergeError: str
    SquashCommits: bool

class CreateMergeRequestResult(BaseModel):
    MergeRequest: MergeRequest

class CreateMergeRequestResponse(BaseModel):
    ResponseMetadata: ResponseMetadata
    Result: CreateMergeRequestResult

# --- Function Definition ---

def create_mr(
    title: str,
    description: str,
    source_branch: str,
    target_branch: str,
    # reviewer_ids: Optional[List[int]] = None,
    # work_item_ids: Optional[List[str]] = None,
) -> CreateMergeRequestResponse:
    url = "https://code.byted.org/api/v2/?Action=CreateMergeRequest"
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'Cookie': config.CODE_COOKIE,
    }
    
    data = {
        "Title": title,
        "Description": description,
        "SourceRepoId": config.LUMI_REPO_ID,
        "TargetRepoId": config.LUMI_REPO_ID,
        "SourceBranch": source_branch,
        "TargetBranch": target_branch,
        "MergeMethod": "merge_commit",
        "RemoveSourceBranchAfterMerge": False,
        "ReviewerIds":  [],
        "WorkItemIds": [],
        "SquashCommits": False,
        "Draft": False
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()