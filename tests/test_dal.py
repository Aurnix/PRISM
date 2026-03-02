"""Tests for Data Access Layer (DAL) implementations."""

import pytest

from prism.data.dal import DataAccessLayer
from prism.data.fixture_dal import FixtureDAL


class TestFixtureDAL:
    """Tests for the fixture-based (read-only) DAL."""

    @pytest.fixture
    def dal(self):
        return FixtureDAL()

    @pytest.mark.asyncio
    async def test_list_accounts(self, dal):
        accounts = await dal.list_accounts()
        # Should return at least some fixture accounts
        assert isinstance(accounts, list)

    @pytest.mark.asyncio
    async def test_get_account_valid_slug(self, dal):
        # First list to find a valid slug
        accounts = await dal.list_accounts()
        if accounts:
            slug = accounts[0].slug
            account = await dal.get_account(slug)
            assert account is not None
            assert account.slug == slug

    @pytest.mark.asyncio
    async def test_get_account_invalid_slug(self, dal):
        account = await dal.get_account("nonexistent_company_slug_xyz")
        assert account is None

    @pytest.mark.asyncio
    async def test_upsert_account_raises(self, dal, sample_account):
        with pytest.raises(NotImplementedError):
            await dal.upsert_account(sample_account)

    @pytest.mark.asyncio
    async def test_update_account_status_raises(self, dal):
        with pytest.raises(NotImplementedError):
            await dal.update_account_status("test", "archived")

    @pytest.mark.asyncio
    async def test_get_dossier_not_found(self, dal):
        result = await dal.get_dossier("PRISM-9999-0001")
        assert result is None


class TestDALInterface:
    """Verify the abstract interface contract."""

    def test_dal_is_abstract(self):
        with pytest.raises(TypeError):
            DataAccessLayer()

    def test_fixture_dal_is_dal(self):
        dal = FixtureDAL()
        assert isinstance(dal, DataAccessLayer)


class TestGetDalFactory:
    def test_returns_fixture_dal_without_db(self):
        from prism.data import get_dal
        dal = get_dal()
        assert isinstance(dal, FixtureDAL)
