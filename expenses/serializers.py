from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from rest_framework import serializers

from expenses.models import Group, GroupMember, Expense, ExpenseSplit, Settlement
from expenses.common import constants as app_constants, messages as app_messages
from users.models import User, Friends
from django.db.models import Q


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['group_name', 'description']

    def create(self, validated_data):
        group = Group.objects.create(**validated_data)
        return group


class GroupMemberSerializer(serializers.ModelSerializer):
    member = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    )

    class Meta:
        model = GroupMember
        fields = ['group', 'member']

    def __init__(self, *args, **kwargs):
        self.owner_id = kwargs.pop('context', {}).get('owner_id')
        super().__init__(*args, **kwargs)

    def validate(self, data):
        members = data.get('member', [])
        for member in members:
            if member.id != self.owner_id and not Friends.objects.filter(
                    Q(user_1_id=self.owner_id, user_2_id=member) | Q(user_1_id=member,
                                                                     user_2_id=self.owner_id)).exists():
                raise serializers.ValidationError("Must be friends to add in group")
        return data

    def create(self, validated_data):
        members = validated_data.pop('member', [])
        group = validated_data.pop('group')

        if not members:
            raise serializers.ValidationError("At least one member must be provided.")

        try:
            with transaction.atomic():
                group_members = self._create_group_members(group, members)
                return group_members[-1] if group_members else None
        except Exception as e:
            raise serializers.ValidationError(f"Failed to add members to group: {str(e)}")

    def _create_group_members(self, group, members):
        group_members = []
        for member in members:
            is_owner = self._is_owner(member)
            if not is_owner:
                if not Friends.objects.filter(Q(user_1_id=self.owner_id, user_2_id=member) | Q(user_1_id=member,
                                                                                               user_2_id=self.owner_id)).exists():
                    raise Exception("Must be friends to add in group")
            group_member = GroupMember.objects.create(
                group=group,
                member=member,
                is_owner=is_owner
            )
            group_members.append(group_member)

        return group_members

    def _is_owner(self, member):
        return member.id == self.owner_id


class ExpenseSplitSerializer(serializers.ModelSerializer):
    split_value = serializers.CharField(write_only=True, allow_null=True)

    class Meta:
        model = ExpenseSplit
        fields = ['split_value', 'split_type', 'expense_user', 'status']


class ExpenseSerializer(serializers.ModelSerializer):
    split_breakup = ExpenseSplitSerializer(many=True, write_only=True)
    balance_amt = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Expense
        fields = ['name', 'balance_amt', 'expense_by', 'split_breakup', 'group']

    def validate(self, data):
        split_breakup = data.get('split_breakup', [])
        expense_by = data.get("expense_by")
        balance_amt = self._decimalize(data.get('balance_amt'))
        if data.get("group"):
            self._validate_group(split_breakup=split_breakup, group_id=data.get("group"))
        else:
            self._validate_friendship(split_breakup=split_breakup, expense_by=expense_by)
        self._validate_split_type_consistency(split_breakup)
        self._validate_payment_breakup(split_breakup, expense_by)
        self._normalize_or_validate_split_values(split_breakup, balance_amt)

        return data

    def create(self, validated_data):
        split_breakup_data = validated_data.pop('split_breakup')
        balance_amt = self._decimalize(validated_data.get('balance_amt'))

        try:
            with transaction.atomic():
                expense = Expense.objects.create(**validated_data)
                self._create_expense_splits(expense, split_breakup_data, balance_amt)
                return expense

        except Exception as e:
            raise serializers.ValidationError(f"Expense creation failed: {str(e)}")

    def _validate_friendship(self, split_breakup, expense_by):
        members = [i.get('expense_user') for i in split_breakup]
        for member in members:
            if member != expense_by and not Friends.objects.filter(
                    Q(user_1_id=expense_by, user_2_id=member) | Q(user_1_id=member,
                                                                  user_2_id=expense_by)).exists():
                raise serializers.ValidationError("Must be friends to add expense")
        return split_breakup

    def _validate_group(self, split_breakup, group_id):
        members = [i.get('expense_user') for i in split_breakup]
        if GroupMember.objects.filter(group_id=group_id, member__in=members).distinct().count() < len(set(members)):
            raise serializers.ValidationError("can't add group_expense with members not in group.")
        return split_breakup

    def _validate_payment_breakup(self, split_breakup, expense_by):

        if not split_breakup:
            raise serializers.ValidationError("Split breakup is required.")

        paid_users = [split.get("expense_user") for split in split_breakup if split.get("status") == "Paid"]

        if not paid_users:
            raise serializers.ValidationError("At least one user must have paid.")

        if expense_by not in paid_users:
            raise serializers.ValidationError("The user who made the expense must have paid.")

        return split_breakup

    def _decimalize(self, value):
        return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def _validate_split_type_consistency(self, split_breakup):
        split_types = {item['split_type'] for item in split_breakup}
        if len(split_types) > 1:
            raise serializers.ValidationError(app_messages.MULTIPLE_SPLIT_TYPE)

    def _normalize_or_validate_split_values(self, split_breakup, balance_amt):
        split_type = split_breakup[0]['split_type'] if split_breakup else None
        split_values = [Decimal(item.get('split_value')) for item in split_breakup if
                        item.get('split_value') is not None]

        if split_values and not split_type == app_constants.SplitType.EQUAL.value:
            total = sum(split_values)
            if split_type == app_constants.SplitType.PERCENTAGE.value and total != 100:
                raise serializers.ValidationError(app_messages.PERCENTAGE_SUM_MISMATCH)
            elif split_type != app_constants.SplitType.PERCENTAGE.value and total != balance_amt:
                raise serializers.ValidationError(app_messages.EXACT_AMT_MISMATCH_ERROR)
        else:
            self._assign_equal_splits(split_breakup, balance_amt)

    def _assign_equal_splits(self, split_breakup, balance_amt):
        user_count = len(split_breakup)
        if user_count == 0:
            raise serializers.ValidationError("At least one split participant is required.")

        split_value = (balance_amt / user_count).quantize(Decimal('0.01'))
        remainder = balance_amt - (split_value * user_count)

        for idx, row in enumerate(split_breakup):
            row["split_value"] = (split_value + remainder).quantize(Decimal('0.01')) if idx == 0 else split_value

    def _create_expense_splits(self, expense, split_breakup_data, balance_amt):
        for split_data in split_breakup_data:
            split_value = self._decimalize(split_data.pop('split_value'))
            amount = self._calculate_split_amount(split_data['split_type'], split_value, balance_amt)

            balance_outstanding = amount if split_data.get(
                "status") != app_constants.SplitExpenseStatus.PAID.value else Decimal('0.00')

            ExpenseSplit.objects.create(
                expense=expense,
                amount=amount,
                balance_outstanding=balance_outstanding,
                settled=balance_outstanding == 0,
                **split_data
            )

    def _calculate_split_amount(self, split_type, split_value, balance_amt):
        if split_type == app_constants.SplitType.PERCENTAGE.value:
            return ((split_value / 100) * balance_amt).quantize(Decimal('0.01'))
        return split_value


class PaymentLinkSerializer(serializers.Serializer):
    expense_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)
    user_id = serializers.IntegerField(required=True)

    def validate(self, data):
        self._validate_expense(data)
        return data

    def _validate_expense(self, data):
        user_id = data.get("user_id")
        expense_id = data.get("expense_id")
        amount = data.get("amount")
        expense_split = ExpenseSplit.objects.filter(expense__id=expense_id, expense_user__id=user_id,
                                                    balance_outstanding__gte=amount)
        if not expense_split.exists():
            raise serializers.ValidationError("Amount is more than outstanding expense amount")
        data['expense_split'] = expense_split.first()
        return data


class SettlementListSerializer(serializers.ModelSerializer):
    expense_user = serializers.SerializerMethodField()
    expense = serializers.SerializerMethodField()

    class Meta:
        model = Settlement
        fields = ["payment_id", 'status', 'amount', 'is_offline', 'expense', 'expense_user', 'created_on']

    def get_expense_user(self, obj):
        return obj.expense_split.expense_user.username

    def get_expense(self, obj):
        return obj.expense_split.expense.name
