def add_subscription_coins(coins, previous_plan, plan, cancelled_on):
    """
    Add an amount of coins to an existing coin value.

    :param coins: Existing coin value
    :type coins: int
    :param previous_plan: Previous subscription plan
    :type previous_plan: dict
    :param plan: New subscription plan
    :type plan: dict
    :param cancelled_on: When a plan has potentially been cancelled
    :type cancelled_on: datetime
    :return: int
    """
    # Some people will try to game the system and cheat us for extra coins.
    #
    # Users should only be able to gain coins via subscription when:
    #   Subscribes for the first time
    #   Subscriber updates to a better plan (one with more coins)
    #
    # That means the following actions should result in no coins:
    #   Subscriber cancels and signs up for the same plan
    #   Subscriber downgrades to a worse plan
    #
   
    previous_plan_coins = 0
    plan_coins = plan["metadata"]["coins"]

    # if previous_plan:
    #     previous_plan_coins = previous_plan["metadata"]["coins"]

    # if cancelled_on is None and plan_coins == previous_plan_coins:
    #     coin_adjustment = plan_coins
    # elif plan_coins <= previous_plan_coins:
    #     return coins
    # else:
    #     # We only want to add the difference between upgrading plans,
    #     # because they were already credited the previous plan's coins.
    #     coin_adjustment = plan_coins - previous_plan_coins

    # return coins + coin_adjustment
 
    return plan_coins
